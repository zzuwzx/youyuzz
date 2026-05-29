# 鱿郁仔仔 — 批量管理器单元测试
# pc-client/backend/tests/test_batch_manager.py
#
# 运行:  cd pc-client\backend && .\venv\Scripts\pytest tests/test_batch_manager.py -v

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.models import InstallStage


# ============================================================
#  Fixtures
# ============================================================

@pytest.fixture
def task_store():
    return {}


@pytest.fixture
def make_batch_task(task_store):
    def _make(task_id="batch_001", game_names=None):
        task_store[task_id] = {
            "stage": InstallStage.QUEUED,
            "percent": 0.0,
            "current_file": None,
            "speed": None,
            "eta": None,
            "total_files": len(game_names or []),
            "completed_files": 0,
            "error": None,
            "game_names": game_names or [],
            "is_batch": True,
            "sub_tasks": [],
        }
        return task_id
    return _make


# ============================================================
#  测试用例
# ============================================================

class TestBatchManager:
    """BatchManager 单元测试。"""

    @pytest.mark.asyncio
    async def test_all_success(self, task_store, make_batch_task):
        """全部成功时应设置 COMPLETED。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=["游戏A", "游戏B"])
        manager = BatchManager()

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=True)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=["游戏A", "游戏B"],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        assert task_store[task_id]["stage"] == InstallStage.COMPLETED
        assert task_store[task_id]["completed_files"] == 2
        assert task_store[task_id]["percent"] == 100.0
        assert len(task_store[task_id]["sub_tasks"]) == 2

    @pytest.mark.asyncio
    async def test_partial_failure(self, task_store, make_batch_task):
        """部分失败时仍应设置 COMPLETED，并记录失败信息。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=["游戏A", "游戏B", "游戏C"])
        manager = BatchManager()

        call_count = 0
        async def mock_run(**kwargs):
            nonlocal call_count
            call_count += 1
            return call_count != 2  # 第二个失败

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=mock_run)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=["游戏A", "游戏B", "游戏C"],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        assert task_store[task_id]["stage"] == InstallStage.COMPLETED
        assert task_store[task_id]["completed_files"] == 3
        assert "失败" in (task_store[task_id]["error"] or "")

    @pytest.mark.asyncio
    async def test_all_failure(self, task_store, make_batch_task):
        """全部失败时应设置 FAILED。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=["游戏A", "游戏B"])
        manager = BatchManager()

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=False)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=["游戏A", "游戏B"],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        assert task_store[task_id]["stage"] == InstallStage.FAILED

    @pytest.mark.asyncio
    async def test_exception_in_pipeline(self, task_store, make_batch_task):
        """管道抛异常时应捕获并继续下一个。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=["游戏A", "游戏B"])
        manager = BatchManager()

        call_count = 0
        async def mock_run(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("网络断开")
            return True

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=mock_run)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=["游戏A", "游戏B"],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        # 第一个失败，第二个成功 → 部分完成
        assert task_store[task_id]["completed_files"] == 2

    @pytest.mark.asyncio
    async def test_sub_tasks_created(self, task_store, make_batch_task):
        """每个游戏应创建对应子任务。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=["A", "B", "C"])
        manager = BatchManager()

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=True)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=["A", "B", "C"],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        assert len(task_store[task_id]["sub_tasks"]) == 3
        # 子任务 ID 格式: batch_001_0, batch_001_1, batch_001_2
        assert task_store[task_id]["sub_tasks"][0] == "batch_001_0"
        assert task_store[task_id]["sub_tasks"][1] == "batch_001_1"
        assert task_store[task_id]["sub_tasks"][2] == "batch_001_2"

    @pytest.mark.asyncio
    async def test_empty_game_names(self, task_store, make_batch_task):
        """空游戏名列表应跳过。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=[])
        manager = BatchManager()

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=True)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=[],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        assert task_store[task_id]["completed_files"] == 0

    @pytest.mark.asyncio
    async def test_blank_names_skipped(self, task_store, make_batch_task):
        """空白游戏名应被跳过。"""
        from services.batch_manager import BatchManager

        task_id = make_batch_task(game_names=["", "  ", "游戏A"])
        manager = BatchManager()

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=True)

        with patch("services.batch_manager.install_pipeline", mock_pipeline):
            await manager.run_batch(
                task_id=task_id,
                game_names=["", "  ", "游戏A"],
                task_store=task_store,
                scraper=MagicMock(),
                disk=MagicMock(),
                mtp_backend=MagicMock(),
            )

        # 只有 "游戏A" 被处理
        assert mock_pipeline.run.call_count == 1
