# 鱿郁仔仔 — 设置 + 授权路由
# pc-client/backend/api/settings.py

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from config import config
from .models import (
    SettingsResponse,
    SettingsUpdateRequest,
    ActivateRequest,
    ActivateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 可动态修改的配置键白名单
_ALLOWED_KEYS = {
    "host", "port", "scraper_headless", "mtp_backend",
    "auth_server_url", "log_level",
}

# 持久化配置文件路径
_PERSIST_PATH = config.DATA_DIR / "settings.json"


def _load_persisted() -> dict[str, Any]:
    """加载已持久化的设置。"""
    if _PERSIST_PATH.exists():
        try:
            return json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_persisted(data: dict[str, Any]) -> None:
    """持久化设置到文件。"""
    _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PERSIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ============================================================
#  GET /api/settings
# ============================================================

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """返回当前配置（含运行时值 + 持久化覆盖）。"""
    persisted = _load_persisted()

    return SettingsResponse(
        host=persisted.get("host", config.HOST),
        port=persisted.get("port", config.PORT),
        version=config.VERSION,
        scraper_headless=persisted.get("scraper_headless", config.SCRAPER_HEADLESS),
        mtp_backend=persisted.get("mtp_backend", config.MTP_PREFERRED_BACKEND),
        auth_server_url=persisted.get("auth_server_url", config.AUTH_SERVER_URL),
        log_level=persisted.get("log_level", config.LOG_LEVEL),
    )


# ============================================================
#  PUT /api/settings
# ============================================================

@router.put("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """更新单个配置项。"""
    key = req.key
    if key not in _ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"不允许修改的配置项: {key}")

    # 类型转换
    value: Any = req.value
    if key in ("port",):
        value = int(value)
    elif key in ("scraper_headless",):
        value = value.lower() in ("true", "1", "yes")

    # 持久化
    persisted = _load_persisted()
    persisted[key] = value
    _save_persisted(persisted)

    # 同步运行时 config
    setattr(config, key.upper() if key == "port" else key, value)

    logger.info("配置已更新: %s = %s", key, value)
    return {"status": "ok", key: value}


# ============================================================
#  POST /api/auth/activate
# ============================================================

@router.post("/auth/activate", response_model=ActivateResponse)
async def activate(req: ActivateRequest):
    """激活码验证。

    Phase 1: 本地放行（调试模式），始终返回成功。
    Phase 2: 转发到 Cloudflare Workers 验证服务。
    """
    logger.info("激活请求: code=%s", req.code)

    # Phase 1 stub：直接放行
    return ActivateResponse(
        success=True,
        message="本地调试模式，已激活",
        license_key="DEBUG-LOCAL-" + req.code,
    )
