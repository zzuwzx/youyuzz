# 鱿郁仔仔 — 安装管道单元测试
# pc-client/backend/tests/test_install_pipeline.py
#
# 运行:  cd pc-client\backend && .\venv\Scripts\pytest tests/test_install_pipeline.py -v

from __future__ import annotations

import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.models import InstallStage


# ============================================================
#  Fixtures
# ============================================================

@pytest.fixture
def task_store():
    """模拟任务存储。"""
    return {}


@pytest.fixture
def make_task(task_store):
    """创建任务并返回 task_id。"""
    def _make(task_id="test_001"):
        task_store[task_id] = {
            "stage": InstallStage.QUEUED,
            "percent": 0.0,
            "current_file": None,
            "speed": None,
            "eta": None,
            "total_files": 0,
            "completed_files": 0,
            "error": None,
        }
        return task_id
    return _make


def _make_search_result(name="塞尔达", raw_url="[百度网盘]：https://pan.baidu.com/s/xxx?pwd=abc"):
    """构造搜索结果 mock。"""
    from scraper.models import CloudDiskLink, DiskType
    result = MagicMock()
    result.name = name
    result.similarity = 0.95
    result.raw_url = raw_url
    link = CloudDiskLink(disk_type=DiskType.BAIDU, url="https://pan.baidu.com/s/xxx", password="abc")
    result.links = [link]
    return result


# ============================================================
#  测试用例
# ============================================================

class TestInstallPipeline:
    """InstallPipeline 单元测试。"""

    @pytest.mark.asyncio
    async def test_search_no_results(self, task_store, make_task):
        """搜索无结果时应设置 FAILED。"""
        from services.install_pipeline import InstallPipeline

        task_id = make_task()
        scraper = AsyncMock()
        scraper.search = AsyncMock(return_value=[])

        pipeline = InstallPipeline()
        result = await pipeline.run(
            task_id=task_id,
            game_name="不存在的游戏",
            task_store=task_store,
            scraper=scraper,
            disk=AsyncMock(),
            mtp_backend=MagicMock(),
        )

        assert result is False
        assert task_store[task_id]["stage"] == InstallStage.FAILED
        assert "搜索无结果" in task_store[task_id]["error"]

    @pytest.mark.asyncio
    async def test_no_disk_links(self, task_store, make_task):
        """搜索结果无网盘链接时应设置 FAILED。"""
        from services.install_pipeline import InstallPipeline

        task_id = make_task()
        scraper = AsyncMock()
        result = MagicMock()
        result.name = "测试游戏"
        result.similarity = 0.9
        result.raw_url = "无链接内容"
        result.links = []
        scraper.search = AsyncMock(return_value=[result])

        pipeline = InstallPipeline()
        ok = await pipeline.run(
            task_id=task_id,
            game_name="测试",
            task_store=task_store,
            scraper=scraper,
            disk=AsyncMock(),
            mtp_backend=MagicMock(),
        )

        assert ok is False
        assert task_store[task_id]["stage"] == InstallStage.FAILED
        assert "网盘链接" in task_store[task_id]["error"]

    @pytest.mark.asyncio
    async def test_save_to_drive_failure(self, task_store, make_task):
        """网盘转存失败时应设置 FAILED。"""
        from services.install_pipeline import InstallPipeline

        task_id = make_task()
        scraper = AsyncMock()
        scraper.search = AsyncMock(return_value=[_make_search_result()])

        disk = AsyncMock()
        disk.save_to_drive = AsyncMock(side_effect=Exception("cookie 过期"))

        pipeline = InstallPipeline()
        ok = await pipeline.run(
            task_id=task_id,
            game_name="塞尔达",
            task_store=task_store,
            scraper=scraper,
            disk=disk,
            mtp_backend=MagicMock(),
        )

        assert ok is False
        assert task_store[task_id]["stage"] == InstallStage.FAILED
        assert "cookie 过期" in task_store[task_id]["error"]

    @pytest.mark.asyncio
    async def test_mtp_not_connected(self, task_store, make_task):
        """MTP 未连接时应设置 FAILED。"""
        from services.install_pipeline import InstallPipeline

        task_id = make_task()
        scraper = AsyncMock()
        scraper.search = AsyncMock(return_value=[_make_search_result()])

        disk = AsyncMock()
        transfer = MagicMock()
        transfer.file_name = "Zelda.nsp"
        transfer.file_id = "f001"
        disk.save_to_drive = AsyncMock(return_value=transfer)
        disk.download = AsyncMock(return_value="/tmp/Zelda.nsp")

        mtp = MagicMock()
        mtp.is_device_connected.return_value = False

        pipeline = InstallPipeline()

        with patch("services.install_pipeline.config") as mock_config:
            mock_config.DOWNLOAD_DIR = Path("/tmp/test_dl")

            with patch("game_files.classifier.GameClassifier") as MockCls:
                scan = MagicMock()
                scan.games = []
                scan.cheats = []
                MockCls.return_value.scan.return_value = scan

                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value = MagicMock(st_size=1024)

                        ok = await pipeline.run(
                            task_id=task_id,
                            game_name="塞尔达",
                            task_store=task_store,
                            scraper=scraper,
                            disk=disk,
                            mtp_backend=mtp,
                        )

        assert ok is False
        assert task_store[task_id]["stage"] == InstallStage.FAILED
        assert "Switch 未连接" in task_store[task_id]["error"]

    @pytest.mark.asyncio
    async def test_task_not_found(self, task_store):
        """task_store 中没有该 task_id 时应返回 False。"""
        from services.install_pipeline import InstallPipeline

        pipeline = InstallPipeline()
        result = await pipeline.run(
            task_id="nonexistent",
            game_name="test",
            task_store=task_store,
            scraper=MagicMock(),
            disk=MagicMock(),
            mtp_backend=MagicMock(),
        )
        assert result is False
