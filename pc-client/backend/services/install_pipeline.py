# 鱿郁仔仔 — 单游戏安装管道
# pc-client/backend/services/install_pipeline.py
#
# 完整流程：搜索 → 网盘转存 → 下载 → 文件分类 → MTP 传输 → 通知
# 被单安装和批量安装共用。

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from config import config
from api.models import InstallStage
from notifications.pushdeer import notifier as pushdeer_notifier

logger = logging.getLogger(__name__)


def _format_eta(seconds: float) -> str:
    """将秒数格式化为人类可读的 ETA 字符串。"""
    if seconds < 0:
        return ""
    s = int(seconds)
    if s < 60:
        return f"{s}秒"
    if s < 3600:
        return f"{s // 60}分{s % 60}秒"
    return f"{s // 3600}时{(s % 3600) // 60}分"


class InstallPipeline:
    """单游戏完整安装管道。

    用法::

        pipeline = InstallPipeline()
        success = await pipeline.run(
            task_id="abc123",
            game_name="塞尔达传说",
            task_store=_tasks,
            scraper=scraper,
            disk=disk,
            mtp_backend=mtp_backend,
        )
    """

    async def run(
        self,
        task_id: str,
        game_name: str,
        task_store: dict,
        scraper,           # GameScraper instance
        disk,              # CloudDiskBase instance (cookie set)
        mtp_backend,       # MTPTransfer instance
    ) -> bool:
        """执行单游戏完整安装管道。

        Args:
            task_id: 任务 ID
            game_name: 游戏名（搜索用）或直接 URL
            task_store: 共享任务存储
            scraper: GameScraper 实例
            disk: 已配置 cookie 的网盘实例
            mtp_backend: MTP 传输后端

        Returns:
            True 如果安装成功，否则 False。
        """
        task = task_store.get(task_id)
        if not task:
            return False

        game_display_name = game_name  # 用于通知

        try:
            # ── 阶段 1: 搜索 ─────────────────────────────────────
            task["stage"] = InstallStage.SCRAPING
            task["percent"] = 0.0
            task["current_file"] = "正在搜索..."
            task["speed"] = None
            task["eta"] = None

            search_results = await scraper.search(game_name, limit=5)
            if not search_results:
                raise RuntimeError(f"搜索无结果: {game_name}")

            # 选择第一个匹配结果
            best = search_results[0]
            game_display_name = best.name
            logger.info("[%s] 搜索命中: %s (相似度 %.2f)", task_id, best.name, best.similarity)

            # 解析网盘链接
            links = best.links
            if not links:
                # 从 raw_url 二次解析
                from scraper.parser import parse_game_url
                links, _, _ = parse_game_url(best.raw_url)

            if not links:
                raise RuntimeError(f"未找到网盘链接: {best.name}")

            # ── 阶段 2: 网盘转存 ─────────────────────────────────
            task["stage"] = InstallStage.SAVING_TO_DISK
            task["percent"] = 0.0
            task["current_file"] = "正在转存到网盘..."

            # 选择第一个可用链接
            target_link = links[0]
            logger.info("[%s] 转存链接: %s (%s)", task_id, target_link.url, target_link.disk_type)

            transfer_task = await disk.save_to_drive(
                share_url=target_link.url,
                passcode=target_link.password or "",
            )
            logger.info("[%s] 转存完成: %s (file_id=%s)", task_id, transfer_task.file_name, transfer_task.file_id)

            # ── 阶段 3: 下载 ─────────────────────────────────────
            task["stage"] = InstallStage.DOWNLOADING
            task["percent"] = 0.0
            task["current_file"] = transfer_task.file_name

            # 准备下载目录
            download_dir = config.DOWNLOAD_DIR
            download_dir.mkdir(parents=True, exist_ok=True)
            dest_path = str(download_dir / transfer_task.file_name)

            download_start = time.monotonic()
            last_progress_time = 0.0

            async def on_download_progress(downloaded: int, total: int, fname: str):
                nonlocal last_progress_time
                now = time.monotonic()
                if now - last_progress_time < 0.3:
                    return  # 限频 ~3Hz
                last_progress_time = now

                if total > 0:
                    task["percent"] = round(downloaded / total * 100, 1)
                    elapsed = now - download_start
                    if elapsed > 0 and downloaded > 0:
                        speed = downloaded / elapsed
                        speed_mb = speed / (1024 * 1024)
                        task["speed"] = f"{speed_mb:.1f} MB/s"
                        remaining = total - downloaded
                        if speed > 0:
                            task["eta"] = _format_eta(remaining / speed)
                task["current_file"] = fname

            await disk.download(
                transfer_task.file_id,
                dest_path,
                on_progress=on_download_progress,
                segments=4,
            )
            task["percent"] = 100.0
            task["speed"] = None
            task["eta"] = None
            logger.info("[%s] 下载完成: %s", task_id, dest_path)

            # ── 阶段 4: 文件分类 ─────────────────────────────────
            task["stage"] = InstallStage.CLASSIFYING
            task["percent"] = 0.0
            task["current_file"] = "正在分类文件..."

            from game_files.classifier import GameClassifier
            classifier = GameClassifier()
            scan_result = classifier.scan(download_dir)

            if not scan_result.games:
                # 下载的可能是压缩包或单文件，尝试直接用下载目录
                logger.warning("[%s] 未分类到游戏文件，使用下载目录直接传输", task_id)
                install_files = [Path(dest_path)]
            else:
                # 按安装顺序排列: 本体 → 更新 → DLC
                scan_result.games.sort(key=lambda g: g.priority)
                install_files = [Path(g.path) for g in scan_result.games]
                # 如果有金手指也加入
                for c in scan_result.cheats:
                    install_files.append(Path(c.path))

            task["total_files"] = len(install_files)
            task["completed_files"] = 0
            logger.info("[%s] 分类完成: %d 个文件", task_id, len(install_files))

            # ── 阶段 5: MTP 传输 ─────────────────────────────────
            task["stage"] = InstallStage.TRANSFERRING_MTP
            task["percent"] = 0.0

            if not mtp_backend.is_device_connected():
                raise RuntimeError("Switch 未连接——请确认 DBI 已启动并连接 USB")

            mtp_start = time.monotonic()

            for idx, file_path in enumerate(install_files):
                file_name = file_path.name
                file_size = file_path.stat().st_size if file_path.exists() else 0

                task["current_file"] = file_name
                task["percent"] = 0.0
                task["speed"] = None
                task["eta"] = None

                logger.info("[%s] MTP 传输 %d/%d: %s (%.1f MB)",
                            task_id, idx + 1, len(install_files), file_name, file_size / (1024 * 1024))

                last_mtp_update = 0.0

                def on_mtp_progress(p):
                    nonlocal last_mtp_update
                    now = time.monotonic()
                    if now - last_mtp_update < 0.2 and p.ratio < 1.0:
                        return
                    last_mtp_update = now

                    task["percent"] = round(p.ratio * 100, 1)
                    if p.elapsed_sec > 0 and p.bytes_done > 0:
                        speed_mb = p.bytes_done / (p.elapsed_sec * 1024 * 1024)
                        task["speed"] = f"{speed_mb:.1f} MB/s"
                    if p.eta_sec > 0:
                        task["eta"] = _format_eta(p.eta_sec)

                # MTP 传输在线程中执行（COM STA apartment）
                from mtp.base import CopyResult, PartitionType
                result = await asyncio.to_thread(
                    mtp_backend.copy_file,
                    str(file_path),
                    PartitionType.SD_CARD,
                    on_mtp_progress,
                )

                if result != CopyResult.OK:
                    raise RuntimeError(f"MTP 传输失败 ({result.name}): {file_name}")

                task["completed_files"] = idx + 1

            # ── 阶段 6: 完成 ─────────────────────────────────────
            task["stage"] = InstallStage.COMPLETED
            task["percent"] = 100.0
            task["current_file"] = None
            task["speed"] = None
            task["eta"] = None
            logger.info("[%s] 安装完成: %s", task_id, game_display_name)

            # PushDeer 通知
            await pushdeer_notifier.notify_install_done(game_display_name, success=True)

            return True

        except Exception as e:
            logger.exception("[%s] 安装管道异常: %s", task_id, e)
            task["stage"] = InstallStage.FAILED
            task["error"] = str(e)

            # PushDeer 失败通知
            await pushdeer_notifier.notify_install_done(
                game_display_name, success=False, error=str(e)
            )

            return False

        finally:
            # 清理下载临时文件
            try:
                if download_dir.exists():
                    shutil.rmtree(download_dir, ignore_errors=True)
                    logger.debug("[%s] 已清理下载目录: %s", task_id, download_dir)
            except Exception:
                pass


# 全局单例
pipeline = InstallPipeline()
