# 鱿郁仔仔 — PushDeer 消息推送
# pc-client/backend/notifications/pushdeer.py

"""PushDeer 推送通知模块。

PushDeer API: POST https://api2.pushdeer.com/message/push
参数: pushkey, text, desp(markdown 可选)

当 push_key 为空时所有操作静默跳过。
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PUSHDEER_API_URL = "https://api2.pushdeer.com/message/push"
REQUEST_TIMEOUT = 10  # seconds


class PushDeerNotifier:
    """PushDeer 推送通知器。

    用法::

        notifier = PushDeerNotifier("PDX123456...")
        await notifier.notify("hello")
        await notifier.notify_install_done("塞尔达传说", True)
        await notifier.notify_batch_done(5, 4, 1, ["马力欧"])
    """

    def __init__(self, push_key: str = "") -> None:
        self._push_key = push_key.strip()

    @property
    def is_configured(self) -> bool:
        return bool(self._push_key)

    def update_key(self, push_key: str) -> None:
        """动态更新 push key（用户修改设置后调用）。"""
        self._push_key = push_key.strip()

    # ── 核心发送 ──────────────────────────────────────────────

    async def notify(self, text: str, desp: str = "") -> bool:
        """发送 PushDeer 推送。

        Args:
            text: 推送标题
            desp: 推送正文（可选，支持 Markdown）

        Returns:
            True 如果推送成功，否则 False。
        """
        if not self._push_key:
            logger.debug("PushDeer key 未配置，跳过推送")
            return False

        payload: dict = {
            "pushkey": self._push_key,
            "text": text,
        }
        if desp:
            payload["desp"] = desp

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(PUSHDEER_API_URL, data=payload)
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") == 0:
                    logger.info("PushDeer 推送成功: %s", text)
                    return True
                else:
                    logger.warning("PushDeer 推送返回错误: %s", result)
                    return False
        except Exception:
            logger.warning("PushDeer 推送失败，已静默忽略", exc_info=True)
            return False

    # ── 业务快捷方法 ──────────────────────────────────────────

    async def notify_install_done(
        self,
        game_name: str,
        success: bool,
        error: str = "",
    ) -> bool:
        """单游戏安装完成/失败通知。"""
        if success:
            text = f"✅ {game_name} 安装完成"
            desp = ""
        else:
            text = f"❌ {game_name} 安装失败"
            desp = f"失败原因: {error}" if error else ""

        return await self.notify(text, desp)

    async def notify_batch_done(
        self,
        total: int,
        success: int,
        failed: int,
        failed_names: list[str] | None = None,
    ) -> bool:
        """批量安装完成汇总通知。"""
        if failed == 0:
            text = f"📦 批量安装全部完成：{success}/{total} 个游戏"
            desp = ""
        else:
            text = f"📦 批量安装完成：成功 {success}/{total}，失败 {failed} 个"
            lines = "\n".join(f"- {name}" for name in (failed_names or []))
            desp = f"失败的游戏:\n{lines}" if lines else ""

        return await self.notify(text, desp)


# 全局单例（由 main.py lifespan 初始化）
notifier = PushDeerNotifier()
