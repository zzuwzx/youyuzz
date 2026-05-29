# 鱿郁仔仔 — 设置 + 授权路由
# pc-client/backend/api/settings.py

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from config import config
from auth.client import activate as auth_activate, get_device_id
from .models import (
    SettingsResponse,
    SettingsUpdateRequest,
    ActivateRequest,
    ActivateResponse,
    AuthStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_KEYS = {
    "host", "port", "scraper_headless", "mtp_backend",
    "auth_server_url", "log_level", "pushdeer_key",
}

_PERSIST_PATH = config.DATA_DIR / "settings.json"


def _load_persisted() -> dict[str, Any]:
    if _PERSIST_PATH.exists():
        try:
            return json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_persisted(data: dict[str, Any]) -> None:
    _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PERSIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    persisted = _load_persisted()
    return SettingsResponse(
        host=persisted.get("host", config.HOST),
        port=persisted.get("port", config.PORT),
        version=config.VERSION,
        scraper_headless=persisted.get("scraper_headless", config.SCRAPER_HEADLESS),
        mtp_backend=persisted.get("mtp_backend", config.MTP_PREFERRED_BACKEND),
        auth_server_url=persisted.get("auth_server_url", config.AUTH_SERVER_URL),
        log_level=persisted.get("log_level", config.LOG_LEVEL),
        pushdeer_key=persisted.get("pushdeer_key", config.PUSHDEER_KEY),
    )


@router.put("/settings")
async def update_settings(req: SettingsUpdateRequest):
    key = req.key
    if key not in _ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"不允许修改的配置项: {key}")

    value: Any = req.value
    if key in ("port",):
        value = int(value)
    elif key in ("scraper_headless",):
        value = value.lower() in ("true", "1", "yes")

    persisted = _load_persisted()
    persisted[key] = value
    _save_persisted(persisted)

    # 同步到 config 对象
    setattr(config, key.upper() if key == "port" else key, value)
    logger.info("配置已更新: %s = %s", key, "***" if "key" in key else value)

    # 如果更新了 pushdeer_key，同步到通知器
    if key == "pushdeer_key":
        from notifications.pushdeer import notifier
        notifier.update_key(value)

    return {"status": "ok", key: value}


@router.post("/auth/activate", response_model=ActivateResponse)
async def activate(req: ActivateRequest):
    logger.info("激活请求: code=%s, server=%s", req.code, bool(config.AUTH_SERVER_URL))

    try:
        result = await auth_activate(req.code, config.DEVICE_ID)
    except Exception as exc:
        logger.exception("激活请求异常")
        raise HTTPException(status_code=502, detail="激活服务请求失败") from exc

    return ActivateResponse(
        success=bool(result.get("success", True)),
        message=result.get("message", ""),
        license_key=result.get("license_key"),
    )


@router.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status():
    is_vip = bool(config.LICENSE_KEY)
    return AuthStatusResponse(
        is_vip=is_vip,
        license_key=config.LICENSE_KEY or None,
        expires_at=None if not config.AUTH_SERVER_URL else None,
    )
