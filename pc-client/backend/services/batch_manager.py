# 鱿郁仔仔 — 批量安装队列管理
# pc-client/backend/services/batch_manager.py
#
# 管理批量安装队列，逐个调用 InstallPipeline。

from __future__ import annotations

import logging
import uuid
from typing import Optional

from api.models import InstallStage
from notifications.pushdeer import notifier as pushdeer_notifier
from .install_pipeline import pipeline as install_pipeline

logger = logging.getLogger(__name__)


class BatchManager:
    """批量安装队列管理器。

    逐个执行游戏安装，失败跳过继续，最终汇总报告。

    用法::

        manager = BatchManager()
        await manager.run_batch(
            task_id="batch_001",
            game_names=["塞尔达传说", "马力欧赛车", "宝可梦紫"],
            task_store=_tasks,
            scraper=scraper,
            disk=disk,
            mtp_backend=mtp_backend,
        )
    """

    async def run_batch(
        self,
        task_id: str,
        game_names: list[str],
        task_store: dict,
        scraper,
        disk,
        mtp_backend,
    ) -> None:
        """执行批量安装。

        Args:
            task_id: 批量任务 ID
            game_names: 游戏名列表
            task_store: 共享任务存储
            scraper: GameScraper 实例
            disk: 已配置 cookie 的网盘实例
            mtp_backend: MTP 传输后端
        """
        batch_task = task_store.get(task_id)
        if not batch_task:
            return

        total = len(game_names)
        batch_task["stage"] = InstallStage.DOWNLOADING  # 批量进行中
        batch_task["total_files"] = total
        batch_task["completed_files"] = 0
        batch_task["sub_tasks"] = []

        succeeded = 0
        failed = 0
        failed_names: list[str] = []

        for idx, game_name in enumerate(game_names):
            game_name = game_name.strip()
            if not game_name:
                continue

            # 创建子任务
            sub_task_id = f"{task_id}_{idx}"
            batch_task["sub_tasks"].append(sub_task_id)

            task_store[sub_task_id] = {
                "stage": InstallStage.QUEUED,
                "percent": 0.0,
                "current_file": None,
                "speed": None,
                "eta": None,
                "total_files": 0,
                "completed_files": 0,
                "error": None,
                "game_name": game_name,
                "batch_parent": task_id,
            }

            # 更新批量任务的当前进度
            batch_task["current_file"] = f"[{idx + 1}/{total}] {game_name}"

            logger.info("[batch:%s] 开始安装 %d/%d: %s", task_id, idx + 1, total, game_name)

            try:
                success = await install_pipeline.run(
                    task_id=sub_task_id,
                    game_name=game_name,
                    task_store=task_store,
                    scraper=scraper,
                    disk=disk,
                    mtp_backend=mtp_backend,
                )

                if success:
                    succeeded += 1
                else:
                    failed += 1
                    failed_names.append(game_name)

            except Exception as e:
                logger.exception("[batch:%s] 子任务异常: %s", sub_task_id, e)
                failed += 1
                failed_names.append(game_name)
                task_store[sub_task_id]["stage"] = InstallStage.FAILED
                task_store[sub_task_id]["error"] = str(e)

            # 更新批量任务进度
            batch_task["completed_files"] = idx + 1
            batch_task["percent"] = round((idx + 1) / total * 100, 1)

        # ── 批量完成 ─────────────────────────────────────────
        if failed == 0:
            batch_task["stage"] = InstallStage.COMPLETED
        elif succeeded == 0:
            batch_task["stage"] = InstallStage.FAILED
            batch_task["error"] = f"全部 {failed} 个游戏安装失败"
        else:
            # 部分成功
            batch_task["stage"] = InstallStage.COMPLETED
            batch_task["error"] = f"{failed} 个游戏安装失败: {', '.join(failed_names)}"

        batch_task["percent"] = 100.0
        batch_task["current_file"] = None

        logger.info(
            "[batch:%s] 批量安装完成: 成功 %d/%d, 失败 %d",
            task_id, succeeded, total, failed,
        )

        # PushDeer 批量完成通知
        await pushdeer_notifier.notify_batch_done(
            total=total,
            success=succeeded,
            failed=failed,
            failed_names=failed_names,
        )


# 全局单例
batch_manager = BatchManager()
