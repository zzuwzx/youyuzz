# 鱿郁仔仔 — 系统路由
# pc-client/backend/api/system.py

from __future__ import annotations

import sys
import time
import logging

from fastapi import APIRouter

from config import config
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

    Phase 1: 仅返回本地版本。
    Phase 2: 查询 Cloudflare Workers 获取最新版本。
    """
    return VersionResponse(
        current=config.VERSION,
        latest=None,        # Phase 2 接入
        update_url=None,    # Phase 2 接入
    )


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
