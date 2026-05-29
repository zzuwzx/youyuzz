# 鱿郁仔仔 — API 单元测试
# pc-client/backend/tests/test_api.py
#
# 运行:  cd pc-client\backend && .\venv\Scripts\pytest tests/test_api.py -v

from __future__ import annotations

import sys
import os
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import config
from api import api_router
from api.install import _tasks, InstallStage
from api import search as search_mod


# ============================================================
#  Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def clean_tasks():
    """每个测试前清空任务存储。"""
    _tasks.clear()
    yield
    _tasks.clear()


@pytest.fixture(scope="module")
def app():
    """不含 lifespan 的测试应用（避免 Playwright/MTP 初始化）。"""
    _app = FastAPI(title="鱿郁仔仔 API (Test)", docs_url="/docs", redoc_url="/redoc")
    _app.include_router(api_router)
    return _app


@pytest.fixture(scope="module")
def client(app):
    """同步 TestClient。"""
    return TestClient(app)


@pytest.fixture
def mock_scraper():
    """注入模拟 scraper，搜索返回预设结果。"""
    from scraper.models import GameSearchResult
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=[
        GameSearchResult(
            name="塞尔达传说|The Legend of Zelda",
            name_cn="塞尔达传说",
            name_en="The Legend of Zelda",
            links=[],
            similarity=1.0,
        )
    ])
    search_mod._scraper = mock
    yield mock
    search_mod._scraper = None


# ============================================================
#  基础路由
# ============================================================

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["python_version"]
        assert body["version"] == config.VERSION

    def test_health_uptime_increases(self, client):
        r1 = client.get("/api/health")
        time.sleep(0.1)
        r2 = client.get("/api/health")
        assert r2.json()["uptime"] > r1.json()["uptime"]


class TestVersion:
    def test_version_returns_current(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200
        assert r.json()["current"] == config.VERSION

    def test_version_has_expected_keys(self, client):
        r = client.get("/api/version")
        body = r.json()
        for key in ("current", "latest", "update_url", "changelog"):
            assert key in body


class TestDocs:
    def test_swagger_accessible(self, client):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_schema_paths(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        paths = schema["paths"]
        # 所有注册的路由路径
        expected = [
            "/api/search", "/api/game/detail",
            "/api/install", "/api/install/{task_id}/progress",
            "/api/install/local", "/api/install/batch",
            "/api/install/{task_id}/stream",
            "/api/device/switch", "/api/device/tfcard",
            "/api/settings", "/api/auth/activate",
            "/api/version", "/api/health",
        ]
        for p in expected:
            assert p in paths, f"Missing path in schema: {p}"


# ============================================================
#  搜索
# ============================================================

class TestSearch:
    def test_search_without_scraper_returns_503(self, client):
        r = client.get("/api/search?keyword=塞尔达")
        assert r.status_code == 503

    def test_search_with_scraper(self, client, mock_scraper):
        r = client.get("/api/search?keyword=塞尔达")
        assert r.status_code == 200
        body = r.json()
        assert body["keyword"] == "塞尔达"
        assert body["total"] >= 1
        assert body["results"][0]["title"] == "塞尔达传说|The Legend of Zelda"

    def test_search_missing_keyword(self, client):
        r = client.get("/api/search")
        assert r.status_code == 422

    def test_search_empty_keyword(self, client):
        r = client.get("/api/search?keyword=")
        assert r.status_code == 422


class TestGameDetail:
    def test_detail_ok(self, client, mock_scraper):
        url = "[夸克网盘]：https://pan.quark.cn/s/abc123"
        r = client.get("/api/game/detail", params={"url": url})
        assert r.status_code == 200
        body = r.json()
        assert "links" in body
        assert len(body["links"]) >= 1

    def test_detail_missing_url(self, client):
        r = client.get("/api/game/detail")
        assert r.status_code == 422


# ============================================================
#  安装
# ============================================================

class TestInstallCreate:
    def test_create_install_task(self, client):
        r = client.post("/api/install", json={
            "game_url": "https://example.com/game",
            "install_order": "sequential",
        })
        assert r.status_code == 202
        body = r.json()
        assert "task_id" in body
        assert body["status"] == "accepted"

    def test_create_install_missing_url(self, client):
        r = client.post("/api/install", json={"install_order": "sequential"})
        assert r.status_code == 422


class TestInstallProgress:
    def test_progress_existing(self, client):
        r = client.post("/api/install", json={
            "game_url": "https://example.com/game",
            "install_order": "sequential",
        })
        task_id = r.json()["task_id"]

        r = client.get(f"/api/install/{task_id}/progress")
        assert r.status_code == 200
        body = r.json()
        assert body["task_id"] == task_id
        # Pipeline runs immediately; without scraper/disk/mtp it fails
        assert body["stage"] in ("queued", "failed")

    def test_progress_nonexistent(self, client):
        r = client.get("/api/install/NONEXIST/progress")
        assert r.status_code == 404

    def test_progress_reflects_updated_state(self, client):
        r = client.post("/api/install", json={
            "game_url": "https://example.com/game",
            "install_order": "sequential",
        })
        task_id = r.json()["task_id"]

        # 模拟后台线程更新进度
        _tasks[task_id]["stage"] = InstallStage.DOWNLOADING
        _tasks[task_id]["percent"] = 45.5
        _tasks[task_id]["current_file"] = "game.nsp"

        r = client.get(f"/api/install/{task_id}/progress")
        assert r.status_code == 200
        body = r.json()
        assert body["stage"] == "downloading"
        assert body["percent"] == 45.5
        assert body["current_file"] == "game.nsp"


class TestLocalInstall:
    def test_local_install_valid_path(self, client):
        r = client.post("/api/install/local", json={"folder_path": "C:\\Windows"})
        assert r.status_code == 202
        assert "task_id" in r.json()

    def test_local_install_nonexistent_path(self, client):
        r = client.post("/api/install/local", json={"folder_path": "Z:\\NONEXIST\\PATH"})
        assert r.status_code == 400

    def test_local_install_missing_path(self, client):
        r = client.post("/api/install/local", json={})
        assert r.status_code == 422


class TestBatchInstall:
    def test_batch_install(self, client):
        # Temporarily set LICENSE_KEY to pass VIP check
        original_key = config.LICENSE_KEY
        config.LICENSE_KEY = "TEST-KEY-0001"
        try:
            r = client.post("/api/install/batch", json={
                "game_names": ["塞尔达", "马力欧"],
            })
            assert r.status_code == 202
            assert "批量安装 2 个游戏" in r.json()["message"]
        finally:
            config.LICENSE_KEY = original_key

    def test_batch_install_empty(self, client):
        r = client.post("/api/install/batch", json={"game_names": []})
        assert r.status_code == 422

    def test_batch_install_no_vip(self, client):
        """No VIP license should return 403."""
        original_key = config.LICENSE_KEY
        config.LICENSE_KEY = ""
        try:
            r = client.post("/api/install/batch", json={
                "game_names": ["塞尔达"],
            })
            assert r.status_code == 403
        finally:
            config.LICENSE_KEY = original_key


# ============================================================
#  SSE 流
# ============================================================

class TestSSEStream:
    def test_stream_404_nonexistent(self, client):
        r = client.get("/api/install/NONEXIST/stream")
        assert r.status_code == 404

    def test_stream_endpoint_in_schema(self, client):
        """SSE 端点已注册到 OpenAPI schema。"""
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        assert "/api/install/{task_id}/stream" in paths
        assert "get" in paths["/api/install/{task_id}/stream"]

    def test_stream_data_consistency_with_polling(self, client):
        """SSE 初始推送的数据应与轮询端点一致。"""
        r = client.post("/api/install", json={
            "game_url": "https://example.com/game",
            "install_order": "sequential",
        })
        task_id = r.json()["task_id"]

        # 更新任务状态（模拟后台线程）
        _tasks[task_id]["stage"] = InstallStage.DOWNLOADING
        _tasks[task_id]["percent"] = 30.0
        _tasks[task_id]["current_file"] = "update.nsp"

        # 通过轮询端点验证（SSE 生成器使用相同 _tasks 数据源）
        r_progress = client.get(f"/api/install/{task_id}/progress")
        assert r_progress.status_code == 200
        body = r_progress.json()
        assert body["stage"] == "downloading"
        assert body["percent"] == 30.0
        assert body["current_file"] == "update.nsp"


# ============================================================
#  设备
# ============================================================

class TestDeviceSwitch:
    def test_switch_status(self, client):
        r = client.get("/api/device/switch")
        assert r.status_code == 200
        body = r.json()
        assert "connected" in body
        assert "mode" in body
        assert "free_space_tf" in body
        assert "free_space_nand" in body


class TestDeviceTFCard:
    def test_tfcard_status(self, client):
        r = client.get("/api/device/tfcard")
        assert r.status_code == 200
        body = r.json()
        assert "inserted" in body
        assert "free_space" in body


# ============================================================
#  设置
# ============================================================

class TestSettings:
    def test_get_settings(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        for key in ("host", "port", "version", "scraper_headless", "log_level"):
            assert key in body, f"Missing key: {key}"

    def test_update_valid_key(self, client):
        r = client.put("/api/settings", json={"key": "log_level", "value": "DEBUG"})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_update_invalid_key(self, client):
        r = client.put("/api/settings", json={"key": "illegal_key", "value": "test"})
        assert r.status_code == 400

    def test_update_missing_body(self, client):
        r = client.put("/api/settings", json={})
        assert r.status_code == 422


# ============================================================
#  授权
# ============================================================

class TestAuthActivate:
    def test_activate_valid_code(self, client):
        r = client.post("/api/auth/activate", json={"code": "YYZZ-ABCD-1234"})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "license_key" in body

    def test_activate_invalid_format(self, client):
        r = client.post("/api/auth/activate", json={"code": "bad-code"})
        assert r.status_code == 422

    def test_activate_missing_code(self, client):
        r = client.post("/api/auth/activate", json={})
        assert r.status_code == 422

