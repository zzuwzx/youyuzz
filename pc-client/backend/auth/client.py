# 鱿郁仔仔 — 授权客户端
# pc-client/backend/auth/client.py

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from config import config

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def get_device_id() -> str:
    return config.DEVICE_ID


def _debug_activate(code: str) -> dict[str, Any]:
    license_key = f"DEBUG-LOCAL-{code}"
    config.LICENSE_KEY = license_key
    return {
        "success": True,
        "message": "本地调试模式，已激活",
        "license_key": license_key,
    }


async def activate(code: str, device_id: str) -> dict[str, Any]:
    if not config.AUTH_SERVER_URL:
        logger.info("AUTH_SERVER_URL 为空，使用本地调试模式激活: code=%s", code)
        return _debug_activate(code)

    async with httpx.AsyncClient(base_url=config.AUTH_SERVER_URL, timeout=_TIMEOUT) as client:
        resp = await client.post("/api/auth/activate", json={
            "code": code,
            "device_id": device_id,
        })
        resp.raise_for_status()
        data = resp.json()

    license_key = data.get("license_key")
    if license_key:
        config.LICENSE_KEY = license_key

    return {
        "success": True,
        "message": data.get("message", "激活成功"),
        "license_key": license_key,
    }


async def verify(license_key: str, device_id: str) -> dict[str, Any]:
    if not config.AUTH_SERVER_URL:
        return {"valid": bool(license_key), "expires_at": None}

    async with httpx.AsyncClient(base_url=config.AUTH_SERVER_URL, timeout=_TIMEOUT) as client:
        resp = await client.post("/api/auth/verify", json={
            "license_key": license_key,
            "device_id": device_id,
        })
        resp.raise_for_status()
        return resp.json()


async def heartbeat(license_key: str, device_id: str) -> dict[str, Any]:
    if not config.AUTH_SERVER_URL:
        return {"ok": True}

    async with httpx.AsyncClient(base_url=config.AUTH_SERVER_URL, timeout=_TIMEOUT) as client:
        resp = await client.post("/api/auth/heartbeat", json={
            "license_key": license_key,
            "device_id": device_id,
        })
        resp.raise_for_status()
        return resp.json()
