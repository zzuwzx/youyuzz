# 鱿郁仔仔 — PushDeer 推送通知单元测试
# pc-client/backend/tests/test_pushdeer.py
#
# 运行:  cd pc-client\backend && .\venv\Scripts\pytest tests/test_pushdeer.py -v

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
#  基本功能
# ============================================================

class TestPushDeerNotifier:
    """PushDeerNotifier 单元测试（全 mock httpx）。"""

    def test_not_configured_by_default(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier()
        assert not n.is_configured

    def test_update_key(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier()
        n.update_key("PDX123")
        assert n.is_configured

    @pytest.mark.asyncio
    async def test_notify_skips_when_no_key(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier()
        result = await n.notify("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_success(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"code": 0}

        with patch("notifications.pushdeer.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = instance

            result = await n.notify("hello", "world")
            assert result is True
            instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_api_error(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"code": -1, "error": "bad key"}

        with patch("notifications.pushdeer.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = instance

            result = await n.notify("test")
            assert result is False

    @pytest.mark.asyncio
    async def test_notify_network_error_silent(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        with patch("notifications.pushdeer.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.post = AsyncMock(side_effect=Exception("network down"))
            MockClient.return_value = instance

            # 不应抛出异常
            result = await n.notify("test")
            assert result is False

    @pytest.mark.asyncio
    async def test_notify_install_done_success(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        with patch.object(n, "notify", new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = True
            result = await n.notify_install_done("塞尔达", True)
            assert result is True
            mock_notify.assert_called_once()
            args = mock_notify.call_args
            assert "塞尔达" in args[0][0]
            assert "完成" in args[0][0]

    @pytest.mark.asyncio
    async def test_notify_install_done_failure(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        with patch.object(n, "notify", new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = True
            result = await n.notify_install_done("马力欧", False, error="MTP断开")
            assert result is True
            args = mock_notify.call_args
            assert "马力欧" in args[0][0]
            assert "失败" in args[0][0]

    @pytest.mark.asyncio
    async def test_notify_batch_done_all_success(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        with patch.object(n, "notify", new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = True
            result = await n.notify_batch_done(5, 5, 0)
            assert result is True
            args = mock_notify.call_args
            assert "全部" in args[0][0]

    @pytest.mark.asyncio
    async def test_notify_batch_done_partial_failure(self):
        from notifications.pushdeer import PushDeerNotifier
        n = PushDeerNotifier("PDX123")

        with patch.object(n, "notify", new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = True
            result = await n.notify_batch_done(5, 3, 2, ["马力欧", "宝可梦"])
            assert result is True
            args = mock_notify.call_args
            assert "失败 2" in args[0][0]
