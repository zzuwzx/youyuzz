"""
鱿郁仔仔 — 客户端自动更新模块
启动时检查 GitHub Release → 下载新版本 → 替换安装

使用方式:
    from services.auto_updater import AutoUpdater
    
    updater = AutoUpdater()
    has_update, info = await updater.check_update()
    if has_update:
        await updater.download_and_install(info)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# GitHub 配置
GITHUB_OWNER = "zzuwzx"  # TODO: 替换为实际用户名
GITHUB_REPO = "youyuzz"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"


@dataclass
class UpdateInfo:
    """更新信息"""
    version: str
    download_url: str
    changelog: str
    sha256: str = ""
    file_size: int = 0


class AutoUpdater:
    """
    自动更新器
    检查 GitHub Release 并下载安装新版本。
    """
    
    def __init__(self, current_version: str = "1.0.0"):
        self.current_version = current_version
        self._download_dir = Path(tempfile.gettempdir()) / "youyuzz_update"
        self._download_dir.mkdir(parents=True, exist_ok=True)
    
    async def check_update(self) -> Tuple[bool, Optional[UpdateInfo]]:
        """
        检查是否有新版本
        
        Returns:
            (has_update, update_info)
        """
        try:
            async with httpx.AsyncClient() as client:
                # 获取最新 release
                response = await client.get(
                    f"{GITHUB_API}/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=10.0,
                )
                
                if response.status_code != 200:
                    logger.warning("获取 release 信息失败: %d", response.status_code)
                    return False, None
                
                data = response.json()
                latest_version = data["tag_name"].lstrip("v")
                
                # 版本比较
                if not self._is_newer(latest_version, self.current_version):
                    logger.info("当前已是最新版本: %s", self.current_version)
                    return False, None
                
                # 解析下载链接
                download_url = ""
                sha256 = ""
                file_size = 0
                
                for asset in data.get("assets", []):
                    name = asset["name"]
                    if name.endswith(".exe") and "Setup" in name:
                        download_url = asset["browser_download_url"]
                        file_size = asset["size"]
                    elif name.endswith(".sha256"):
                        # 下载校验和文件
                        sha256_resp = await client.get(asset["browser_download_url"])
                        if sha256_resp.status_code == 200:
                            sha256 = sha256_resp.text.strip().split()[0]
                
                if not download_url:
                    logger.warning("未找到安装包下载链接")
                    return False, None
                
                update_info = UpdateInfo(
                    version=latest_version,
                    download_url=download_url,
                    changelog=data.get("body", ""),
                    sha256=sha256,
                    file_size=file_size,
                )
                
                logger.info("发现新版本: %s -> %s", self.current_version, latest_version)
                return True, update_info
                
        except Exception:
            logger.warning("检查更新失败", exc_info=True)
            return False, None
    
    def _is_newer(self, latest: str, current: str) -> bool:
        """比较版本号"""
        try:
            latest_parts = [int(x) for x in latest.split(".")]
            current_parts = [int(x) for x in current.split(".")]
            
            # 补齐长度
            while len(latest_parts) < 3:
                latest_parts.append(0)
            while len(current_parts) < 3:
                current_parts.append(0)
            
            return latest_parts > current_parts
        except ValueError:
            return False
    
    async def download_and_install(self, update_info: UpdateInfo) -> bool:
        """
        下载并安装更新
        
        Args:
            update_info: 更新信息
        
        Returns:
            是否成功
        """
        try:
            # 下载安装包
            installer_path = self._download_dir / f"youyuzz_setup_{update_info.version}.exe"
            
            logger.info("开始下载更新: %s", update_info.download_url)
            
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", update_info.download_url, timeout=300.0) as response:
                    if response.status_code != 200:
                        logger.error("下载失败: %d", response.status_code)
                        return False
                    
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    
                    with open(installer_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 进度回调（每 1MB）
                            if downloaded % (1024 * 1024) == 0:
                                progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                logger.info("下载进度: %.1f%%", progress)
            
            logger.info("下载完成: %s", installer_path)
            
            # 校验 SHA256
            if update_info.sha256:
                if not self._verify_sha256(installer_path, update_info.sha256):
                    logger.error("SHA256 校验失败")
                    return False
                logger.info("SHA256 校验通过")
            
            # 启动安装程序
            logger.info("启动安装程序...")
            subprocess.Popen(
                [str(installer_path), "/S"],  # /S = 静默安装
                cwd=str(self._download_dir),
            )
            
            # 退出当前程序
            logger.info("安装程序已启动，当前程序将退出")
            sys.exit(0)
            
        except Exception:
            logger.error("安装更新失败", exc_info=True)
            return False
    
    def _verify_sha256(self, file_path: Path, expected_hash: str) -> bool:
        """校验文件 SHA256"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest().lower() == expected_hash.lower()
    
    async def check_and_update(self) -> bool:
        """
        检查并执行更新（便捷方法）
        
        Returns:
            是否有更新（不表示是否安装成功）
        """
        has_update, update_info = await self.check_update()
        if has_update and update_info:
            return await self.download_and_install(update_info)
        return False