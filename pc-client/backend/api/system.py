# 鱿郁仔仔 — 系统路由
# pc-client/backend/api/system.py

from __future__ import annotations

import sys
import time
import logging

from fastapi import APIRouter

from config import config
from services.auto_updater import AutoUpdater
from .models import VersionResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 服务启动时间戳
_started_at = time.time()


# ============================================================
#  GET /api/version
# ============================================================

@router.get("/version", response_model=VersionResponse)
async def get_version():
    """返回版本信息。

    查询 GitHub Release 获取最新版本。
    """
    # 检查更新
    latest_version = None
    update_url = None
    changelog = None
    
    try:
        updater = AutoUpdater(current_version=config.VERSION)
        has_update, update_info = await updater.check_update()
        if has_update and update_info:
            latest_version = update_info.version
            update_url = update_info.download_url
            changelog = update_info.changelog
    except Exception:
        pass
    
    return VersionResponse(
        current=config.VERSION,
        latest=latest_version,
        update_url=update_url,
        changelog=changelog,
    )



# ============================================================
#  GET /api/check-update
# ============================================================

@router.get("/check-update")
async def check_update():
    """手动检查更新"""
    try:
        updater = AutoUpdater(current_version=config.VERSION)
        has_update, update_info = await updater.check_update()
        
        if has_update and update_info:
            return {
                "has_update": True,
                "current_version": config.VERSION,
                "latest_version": update_info.version,
                "download_url": update_info.download_url,
                "changelog": update_info.changelog,
                "file_size": update_info.file_size,
            }
        else:
            return {
                "has_update": False,
                "current_version": config.VERSION,
                "message": "当前已是最新版本",
            }
    except Exception as e:
        logger.error("检查更新失败: %s", str(e))
        return {
            "has_update": False,
            "current_version": config.VERSION,
            "error": str(e),
        }



# ============================================================
#  GET /api/lan-status
# ============================================================

@router.get("/lan-status")
async def get_lan_status():
    """获取局域网加速状态"""
    try:
        from services.lan_accelerator import get_accelerator
        accelerator = get_accelerator()
        status = accelerator.get_status()
        return status
    except Exception as e:
        logger.error("获取局域网状态失败: %s", str(e))
        return {
            "is_lan": False,
            "error": str(e),
        }


# ============================================================
#  GET /api/health
# ============================================================

@router.get("/health", response_model=HealthResponse)
async def health():
    """健康检查。"""
    return HealthResponse(
        status="ok",
        python_version=sys.version.split()[0],
        uptime=round(time.time() - _started_at, 2),
        version=config.VERSION,
    )