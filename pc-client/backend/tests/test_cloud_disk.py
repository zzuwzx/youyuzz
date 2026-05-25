"""Tests for cloud_disk module.

Uses pytest + pytest-mock + httpx mock transports to simulate
Quark API responses without real network calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import httpx
import pytest

from cloud_disk import (
    DiskType,
    QuarkDisk,
    create_disk,
    TransferTask,
    CookieExpiredError,
    RateLimitedError,
    LinkExpiredError,
)


# ---------------------------------------------------------------------------
# Mock response helpers
# ---------------------------------------------------------------------------

def _mock_response(
    status: int = 200,
    json_data: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> httpx.Response:
    """Build a fake httpx.Response."""
    return httpx.Response(
        status_code=status,
        json=json_data or {},
        headers=headers or {},
        request=httpx.Request("GET", "https://test.local"),
    )


# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def disk() -> QuarkDisk:
    """Return a fresh QuarkDisk with a valid-looking cookie."""
    d = QuarkDisk()
    d.set_cookie(
        "__pus=test_pus_value; __pus_csrf=test_csrf; "
        "user_id=12345; token=abcdef"
    )
    return d


# ---------------------------------------------------------------------------
# Cookie validation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_cookie_success(disk, mocker):
    """Cookie validation succeeds when the endpoint returns user info."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "code": 0,
        "data": {"nickname": "TestUser", "avatar": "https://..."},
    })
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    result = await disk.validate_cookie()
    assert result is True


@pytest.mark.asyncio
async def test_validate_cookie_no_cookie():
    """Missing cookie raises immediately."""
    disk = QuarkDisk()
    with pytest.raises(CookieExpiredError, match="No cookie set"):
        await disk.validate_cookie()


@pytest.mark.asyncio
async def test_validate_cookie_missing_key():
    """Cookie without __pus key raises."""
    disk = QuarkDisk()
    disk.set_cookie("user_id=123; token=xyz")
    with pytest.raises(CookieExpiredError, match="missing required key"):
        await disk.validate_cookie()


@pytest.mark.asyncio
async def test_validate_cookie_401(disk, mocker):
    """HTTP 401 triggers CookieExpiredError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(401, {"code": -100})
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(CookieExpiredError):
        await disk.validate_cookie()


@pytest.mark.asyncio
async def test_validate_cookie_login_redirect(disk, mocker):
    """Redirect to passport/login URL triggers CookieExpiredError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = httpx.Response(
        status_code=302,
        headers={"location": "https://pan.quark.cn/passport/login"},
        request=httpx.Request("GET", "https://test.local"),
    )
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(CookieExpiredError):
        await disk.validate_cookie()


@pytest.mark.asyncio
async def test_validate_cookie_no_nickname(disk, mocker):
    """Response with empty nickname raises CookieExpiredError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "code": 0,
        "data": {"nickname": ""},
    })
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(CookieExpiredError, match="No user identity"):
        await disk.validate_cookie()


# ---------------------------------------------------------------------------
# Share URL parsing tests
# ---------------------------------------------------------------------------

def test_is_my_url_quark():
    assert QuarkDisk.is_my_url("https://pan.quark.cn/s/abc123") is True
    assert QuarkDisk.is_my_url("pan.quark.cn/s/xyz789") is True


def test_is_my_url_not_quark():
    assert QuarkDisk.is_my_url("https://pan.baidu.com/s/123") is False
    assert QuarkDisk.is_my_url("https://example.com") is False


def test_parse_share_url():
    result = QuarkDisk.parse_share_url("https://pan.quark.cn/s/abc123?extra")
    assert result == {"pwd_id": "abc123"}


def test_parse_share_url_invalid():
    assert QuarkDisk.parse_share_url("https://pan.baidu.com/s/123") is None


def test_extract_pwd_id():
    assert QuarkDisk._extract_pwd_id("https://pan.quark.cn/s/abc123") == "abc123"


def test_extract_pwd_id_invalid():
    with pytest.raises(ValueError, match="Not a valid Quark share URL"):
        QuarkDisk._extract_pwd_id("https://example.com")


# ---------------------------------------------------------------------------
# save_to_drive tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_to_drive_single_file(disk, mocker):
    """save_to_drive saves the first non-directory file.

    API call sequence:
      1. POST get share token
      2. GET share files page 1 (returns < 100 -> early break)
      3. POST save to drive
    """
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _mock_response(200, {
                "code": 0,
                "data": {"stoken": "st_abc123"},
            })
        elif call_count == 2:
            return _mock_response(200, {
                "code": 0,
                "data": {
                    "title": "Test Share",
                    "list": [{
                        "fid": "fid_001",
                        "file_name": "game.nsp",
                        "size": 123456789,
                        "dir": False,
                        "share_fid_token": "fid_token_001",
                        "pdir_fid": "0",
                    }],
                },
            })
        elif call_count == 3:
            return _mock_response(200, {
                "code": 0,
                "data": {"task_id": "task_001"},
            })
        return _mock_response(500)

    mock_client = mocker.AsyncMock()
    mock_client.request.side_effect = side_effect
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    task = await disk.save_to_drive("https://pan.quark.cn/s/abc123")
    assert isinstance(task, TransferTask)
    assert task.disk_type == DiskType.QUARK
    assert task.share_id == "abc123"
    assert task.file_name == "game.nsp"
    assert task.file_id == "fid_001"
    assert task.size_bytes == 123456789


@pytest.mark.asyncio
async def test_save_to_drive_empty_share(disk, mocker):
    """Empty share raises ValueError."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _mock_response(200, {"code": 0, "data": {"stoken": "st_xyz"}})
        elif call_count == 2:
            return _mock_response(200, {"code": 0, "data": {"title": "Empty", "list": []}})
        return _mock_response(500)

    mock_client = mocker.AsyncMock()
    mock_client.request.side_effect = side_effect
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(ValueError, match="No files found"):
        await disk.save_to_drive("https://pan.quark.cn/s/empty")


# ---------------------------------------------------------------------------
# get_download_link tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_download_link(disk, mocker):
    """get_download_link returns a URL from the API."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "code": 0,
        "data": [{"download_url": "https://dl.quark.cn/abc/def?token=xxx"}],
    })
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    url = await disk.get_download_link("fid_001")
    assert url == "https://dl.quark.cn/abc/def?token=xxx"


@pytest.mark.asyncio
async def test_get_download_link_empty(disk, mocker):
    """Empty data array raises ValueError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "code": 0, "data": [],
    })
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(ValueError, match="No download info"):
        await disk.get_download_link("fid_bad")


# ---------------------------------------------------------------------------
# download tests
# ---------------------------------------------------------------------------

class _FakeStreamCtx:
    """Simulate the object returned by ``httpx.AsyncClient.stream()``.

    Implements async context manager protocol so that
    ``async with client.stream(...) as resp`` works as expected.
    """

    def __init__(self, status_code: int, headers: dict, data: bytes,
                 chunk_size: int = 1024 * 256):
        self.status_code = status_code
        self.headers = headers
        self._data = data
        self._chunk_size = chunk_size

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def aiter_bytes(self, chunk_size: int = 1024):
        for i in range(0, len(self._data), chunk_size):
            yield self._data[i:i + chunk_size]


@pytest.mark.asyncio
async def test_download_stream(disk, mocker, tmp_path):
    """Download streams to a local file with progress callback."""
    dest = tmp_path / "game.nsp"
    test_data = b"x" * 1024 * 10  # 10 KB

    mocker.patch.object(
        disk, "get_download_link", return_value="https://dl.quark.cn/test"
    )

    ctx = _FakeStreamCtx(
        status_code=200,
        headers={"Content-Length": str(len(test_data))},
        data=test_data,
    )

    # Use MagicMock (not AsyncMock) so stream_client.stream() returns ctx
    # directly rather than wrapping it in a coroutine.
    mock_stream_client = mocker.MagicMock()
    mock_stream_client.stream.return_value = ctx
    mock_stream_client.aclose = mocker.AsyncMock()
    mocker.patch(
        "cloud_disk.kuake.httpx.AsyncClient",
        return_value=mock_stream_client,
    )

    progress_calls = []
    async def on_progress(dl, total, name):
        progress_calls.append((dl, total, name))

    result = await disk.download(
        "fid_001",
        str(dest),
        on_progress=on_progress,
        resume=False,
    )
    assert result == str(dest.absolute())
    assert dest.exists()
    assert dest.stat().st_size == len(test_data)
    assert len(progress_calls) > 0
    assert progress_calls[-1][0] == len(test_data)


@pytest.mark.asyncio
async def test_download_resume(disk, mocker, tmp_path):
    """Resume download appends to an existing file."""
    dest = tmp_path / "partial.nsp"
    existing = b"a" * 500
    remaining = b"b" * 500
    dest.write_bytes(existing)

    mocker.patch.object(
        disk, "get_download_link", return_value="https://dl.quark.cn/test"
    )

    ctx = _FakeStreamCtx(
        status_code=206,
        headers={"Content-Range": "bytes 500-999/1000"},
        data=remaining,
    )

    mock_stream_client = mocker.MagicMock()
    mock_stream_client.stream.return_value = ctx
    mock_stream_client.aclose = mocker.AsyncMock()
    mocker.patch(
        "cloud_disk.kuake.httpx.AsyncClient",
        return_value=mock_stream_client,
    )

    result = await disk.download("fid_001", str(dest), resume=True)
    assert dest.stat().st_size == 1000
    assert dest.read_bytes() == existing + remaining


# ---------------------------------------------------------------------------
# Cookie parsing tests
# ---------------------------------------------------------------------------

def test_parse_cookie():
    raw = " a=1; b=2 ; c=3"
    parsed = QuarkDisk._parse_cookie(raw)
    assert parsed == {"a": "1", "b": "2", "c": "3"}


def test_parse_cookie_empty():
    assert QuarkDisk._parse_cookie("") == {}


def test_parse_cookie_no_equals():
    assert QuarkDisk._parse_cookie("a; b=2") == {"b": "2"}


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

def test_create_disk_quark():
    d = create_disk(DiskType.QUARK)
    assert isinstance(d, QuarkDisk)


def test_create_disk_baidu():
    d = create_disk(DiskType.BAIDU)
    from cloud_disk.baidu import BaiduDisk
    assert isinstance(d, BaiduDisk)


def test_create_disk_aliyun():
    d = create_disk(DiskType.ALIYUN)
    from cloud_disk.aliyun import AliyunDisk
    assert isinstance(d, AliyunDisk)


# ---------------------------------------------------------------------------
# Rate limit and error tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limited(disk, mocker):
    """Rate limiting (429) raises RateLimitedError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(
        429, {"code": -1}, headers={"Retry-After": "30"}
    )
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(RateLimitedError) as exc_info:
        await disk.validate_cookie()
    assert exc_info.value.retry_after == 30


@pytest.mark.asyncio
async def test_server_error(disk, mocker):
    """5xx server errors raise RateLimitedError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(500, {"code": -1})
    mocker.patch.object(disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(RateLimitedError):
        await disk.validate_cookie()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

def test_disk_type_str():
    assert str(DiskType.QUARK) == "quark"
    assert DiskType.QUARK.value == "quark"


def test_cookie_expired_error():
    e = CookieExpiredError(DiskType.QUARK)
    assert "quark" in str(e).lower()


def test_rate_limited_error():
    e = RateLimitedError(DiskType.QUARK)
    assert e.retry_after == 60


def test_link_expired_error():
    e = LinkExpiredError(DiskType.QUARK, "test.nsp")
    assert "test.nsp" in str(e)


import time

# ===========================================================================
# Baidu Netdisk tests
# ===========================================================================

from cloud_disk.baidu import BaiduDisk


@pytest.fixture
def bd_disk() -> BaiduDisk:
    """Fresh BaiduDisk with valid-looking cookie."""
    d = BaiduDisk()
    d.set_cookie("BDUSS=test_bduss_value; STOKEN=test_stoken; BDSTOKEN=test_bdstoken")
    return d


# -- URL parsing ---------------------------------------------------------

def test_baidu_is_my_url():
    assert BaiduDisk.is_my_url("https://pan.baidu.com/s/1abc_def") is True
    assert BaiduDisk.is_my_url("https://pan.baidu.com/share/init?surl=xyz789") is True


def test_baidu_is_my_url_not():
    assert BaiduDisk.is_my_url("https://pan.quark.cn/s/123") is False


def test_baidu_parse_share_url():
    r = BaiduDisk.parse_share_url("https://pan.baidu.com/s/1abc-def_ghi")
    assert r == {"surl": "abc-def_ghi"}


def test_baidu_parse_share_url_init():
    r = BaiduDisk.parse_share_url("https://pan.baidu.com/share/init?surl=xyz789")
    assert r == {"surl": "xyz789"}


def test_baidu_extract_surl():
    assert BaiduDisk._extract_surl("https://pan.baidu.com/s/1abc123") == "abc123"


def test_baidu_extract_surl_invalid():
    with pytest.raises(ValueError):
        BaiduDisk._extract_surl("https://example.com")


# -- Cookie validation ----------------------------------------------------

@pytest.mark.asyncio
async def test_baidu_validate_cookie_success(bd_disk, mocker):
    """Valid cookie returns True."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "errno": 0,
        "uk": 123456,
        "bdstoken": "bt_xxx",
        "records": [],
    }, headers={"content-type": "application/json"})
    mocker.patch.object(bd_disk, "_ensure_client", return_value=mock_client)

    result = await bd_disk.validate_cookie()
    assert result is True


@pytest.mark.asyncio
async def test_baidu_validate_cookie_no_bduss():
    disk = BaiduDisk()
    disk.set_cookie("OTHER=123; COOKIE=456")
    with pytest.raises(CookieExpiredError, match="BDUSS"):
        await disk.validate_cookie()


@pytest.mark.asyncio
async def test_baidu_validate_cookie_expired(bd_disk, mocker):
    """errno indicating expired session."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "errno": -6,  # expired
    }, headers={"content-type": "application/json"})
    mocker.patch.object(bd_disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(CookieExpiredError):
        await bd_disk.validate_cookie()


# -- save_to_drive --------------------------------------------------------

@pytest.mark.asyncio
async def test_baidu_save_to_drive(bd_disk, mocker):
    """Full save flow: get share info -> list files -> transfer."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # GET share init page (HTML) -- must be httpx.Response
            import httpx as _httpx2
            return _httpx2.Response(
                status_code=200,
                text=(
                    '{"errno":0}'
                    + '<script>window.yunData={"bdstoken":"bt_scraped",'
                    + '"shareid":"12345","uk":"67890","logid":"lg001"};</script>'
                ),
                headers={"content-type": "text/html"},
                request=_httpx2.Request("GET", "https://test.local"),
            )
        elif call_count == 2:
            # GET share file list
            return _mock_response(200, {
                "errno": 0,
                "records": [{
                    "fs_id": 111222333,
                    "server_filename": "zelda.nsp",
                    "size": 14000000000,
                    "isdir": 0,
                    "path": "/",
                    "category": 6,
                }],
            }, headers={"content-type": "application/json"})
        elif call_count == 3:
            # POST transfer
            return _mock_response(200, {
                "errno": 0,
            }, headers={"content-type": "application/json"})
        return _mock_response(500)

    mock_client = mocker.AsyncMock()
    mock_client.request.side_effect = side_effect
    # Also need the GET for share init (returns text)
    mock_client.get = mocker.AsyncMock(return_value=_mock_response(200))

    mocker.patch.object(bd_disk, "_ensure_client", return_value=mock_client)
    # Override _fetch_bdstoken to return scraped value
    mocker.patch.object(bd_disk, "_fetch_bdstoken", return_value="bt_scraped")

    task = await bd_disk.save_to_drive("https://pan.baidu.com/s/1abc123")
    assert task.disk_type == DiskType.BAIDU
    assert task.file_name == "zelda.nsp"
    assert task.file_id == "111222333"
    assert task.size_bytes == 14000000000


# -- get_download_link ----------------------------------------------------

@pytest.mark.asyncio
async def test_baidu_get_download_link(bd_disk, mocker):
    """get_download_link returns the dlink from API response."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "errno": 0,
        "dlink": [{"dlink": "https://d.pcs.baidu.com/file/xxx"}],
    }, headers={"content-type": "application/json"})
    mocker.patch.object(bd_disk, "_ensure_client", return_value=mock_client)
    mocker.patch.object(bd_disk, "_fetch_bdstoken", return_value="bt_test")

    url = await bd_disk.get_download_link("111222333")
    assert url == "https://d.pcs.baidu.com/file/xxx"


# -- download -------------------------------------------------------------

@pytest.mark.asyncio
async def test_baidu_download(bd_disk, mocker, tmp_path):
    """Download streams to local file."""
    dest = tmp_path / "baidu_game.nsp"
    test_data = b"b" * 5120

    mocker.patch.object(bd_disk, "get_download_link",
                        return_value="https://d.pcs.baidu.com/dl")
    mocker.patch.object(bd_disk, "_fetch_bdstoken", return_value="bt_test")

    ctx = _FakeStreamCtx(200, {"Content-Length": str(len(test_data))}, test_data)
    mock_sc = mocker.MagicMock()
    mock_sc.stream.return_value = ctx
    mock_sc.aclose = mocker.AsyncMock()
    mocker.patch("cloud_disk.baidu.httpx.AsyncClient", return_value=mock_sc)

    result = await bd_disk.download("111222333", str(dest))
    assert dest.exists()
    assert dest.stat().st_size == len(test_data)


# ===========================================================================
# Alibaba Cloud Drive tests
# ===========================================================================

from cloud_disk.aliyun import AliyunDisk


@pytest.fixture
def aliyun_disk(mocker) -> AliyunDisk:
    """AliyunDisk pre-loaded with a refresh_token."""
    d = AliyunDisk()
    d.set_refresh_token("rt_test123")
    # Pre-set tokens to skip auth exchange in most tests
    d._access_token = "at_fake_token"
    d._token_expire_at = 9999999999.0  # far-future expiry
    d._drive_id = "drive_001"
    return d


# Helper: successful token refresh response
ALIYUN_AUTH_OK = _mock_response(200, {
    "access_token": "at_new_token",
    "refresh_token": "rt_new",
    "expires_in": 7200,
    "user_id": "u_001",
    "default_drive_id": "drive_001",
})


# -- URL parsing ---------------------------------------------------------

def test_aliyun_is_my_url():
    assert AliyunDisk.is_my_url("https://www.alipan.com/s/abc123") is True
    assert AliyunDisk.is_my_url("https://www.aliyundrive.com/s/xyz789") is True


def test_aliyun_is_my_url_not():
    assert AliyunDisk.is_my_url("https://pan.quark.cn/s/123") is False


def test_aliyun_parse_share_url():
    r = AliyunDisk.parse_share_url("https://www.alipan.com/s/abc456")
    assert r == {"share_id": "abc456"}


def test_aliyun_extract_share_id():
    assert AliyunDisk._extract_share_id("https://www.alipan.com/s/abc456") == "abc456"


def test_aliyun_extract_share_id_invalid():
    with pytest.raises(ValueError):
        AliyunDisk._extract_share_id("https://example.com")


# -- Cookie / token validation -------------------------------------------

@pytest.mark.asyncio
async def test_aliyun_validate_cookie_success(aliyun_disk, mocker):
    """Pre-loaded token passes validation."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "code": "Success",
        "user_name": "testuser",
        "user_id": "u_001",
        "default_drive_id": "drive_001",
    })
    mocker.patch.object(aliyun_disk, "_ensure_client", return_value=mock_client)

    result = await aliyun_disk.validate_cookie()
    assert result is True


@pytest.mark.asyncio
async def test_aliyun_validate_cookie_expired(mocker):
    """No token at all raises CookieExpiredError."""
    d = AliyunDisk()
    with pytest.raises(CookieExpiredError):
        await d.validate_cookie()


@pytest.mark.asyncio
async def test_aliyun_token_refresh_on_401(aliyun_disk, mocker):
    """401 triggers token clear and CookieExpiredError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(401, {
        "code": "AccessTokenInvalid",
    })
    mocker.patch.object(aliyun_disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(CookieExpiredError):
        await aliyun_disk.validate_cookie()
    assert aliyun_disk._access_token == ""


# -- save_to_drive --------------------------------------------------------

@pytest.mark.asyncio
async def test_aliyun_save_to_drive(aliyun_disk, mocker):
    """Full save: share token -> list -> copy."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _mock_response(200, {"code": "Success", "share_token": "st_001"})
        elif call_count == 2:
            return _mock_response(200, {
                "code": "Success",
                "items": [{
                    "file_id": "f_001",
                    "name": "mario.xci",
                    "size": 8000000000,
                    "type": "file",
                    "drive_id": "drive_001",
                }],
                "next_marker": "",
            })
        elif call_count == 3:
            return _mock_response(200, {
                "code": "Success",
                "responses": [{
                    "status": 200,
                    "body": {"file_id": "f_copied_001"},
                }],
            })
        return _mock_response(500)

    mock_client = mocker.AsyncMock()
    mock_client.request.side_effect = side_effect
    mocker.patch.object(aliyun_disk, "_ensure_client", return_value=mock_client)

    task = await aliyun_disk.save_to_drive("https://www.alipan.com/s/test123")
    assert task.disk_type == DiskType.ALIYUN
    assert task.file_name == "mario.xci"
    assert task.file_id == "f_copied_001"
    assert task.size_bytes == 8000000000


# -- get_download_link ----------------------------------------------------

@pytest.mark.asyncio
async def test_aliyun_get_download_link(aliyun_disk, mocker):
    """Returns download URL."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(200, {
        "code": "Success",
        "url": "https://dl.aliyundrive.com/file/xxx?expire=...",
    })
    mocker.patch.object(aliyun_disk, "_ensure_client", return_value=mock_client)

    url = await aliyun_disk.get_download_link("f_001")
    assert url.startswith("https://dl.aliyundrive.com/")


# -- download -------------------------------------------------------------

@pytest.mark.asyncio
async def test_aliyun_download(aliyun_disk, mocker, tmp_path):
    """Download streams to local file."""
    dest = tmp_path / "aliyun_game.xci"
    test_data = b"a" * 4096

    mocker.patch.object(aliyun_disk, "get_download_link",
                        return_value="https://dl.aliyundrive.com/test")

    ctx = _FakeStreamCtx(200, {"Content-Length": str(len(test_data))}, test_data)
    mock_sc = mocker.MagicMock()
    mock_sc.stream.return_value = ctx
    mock_sc.aclose = mocker.AsyncMock()
    mocker.patch("cloud_disk.aliyun.httpx.AsyncClient", return_value=mock_sc)

    result = await aliyun_disk.download("f_001", str(dest))
    assert dest.exists()
    assert dest.stat().st_size == len(test_data)


# -- Rate limit tests for Baidu/Aliyun ------------------------------------

@pytest.mark.asyncio
async def test_baidu_rate_limited(bd_disk, mocker):
    """429 triggers RateLimitedError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(429, {},
        headers={"Retry-After": "45", "content-type": "application/json"})
    mocker.patch.object(bd_disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(RateLimitedError) as exc_info:
        await bd_disk.validate_cookie()
    assert exc_info.value.retry_after == 45


@pytest.mark.asyncio
async def test_aliyun_rate_limited(aliyun_disk, mocker):
    """429 triggers RateLimitedError."""
    mock_client = mocker.AsyncMock()
    mock_client.request.return_value = _mock_response(429, {},
        headers={"Retry-After": "30"})
    mocker.patch.object(aliyun_disk, "_ensure_client", return_value=mock_client)

    with pytest.raises(RateLimitedError):
        await aliyun_disk.validate_cookie()

# ===========================================================================
# login_via_browser tests
# ===========================================================================

@pytest.mark.asyncio
async def test_login_via_browser_detects_cookies(mocker):
    """Simulate browser cookie polling — detect __pus and save."""
    from cloud_disk.kuake import QuarkDisk

    # Mock playwright internals
    mock_cookies_page1 = [{"name": "other", "value": "x"}]
    mock_cookies_page2 = [
        {"name": "__pus", "value": "pus_val"},
        {"name": "__pus_csrf", "value": "csrf_val"},
    ]

    poll_count = 0

    class FakeContext:
        async def new_page(self):
            return FakePage()
        async def cookies(self):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 2:
                return mock_cookies_page2
            return mock_cookies_page1

    class FakePage:
        async def goto(self, url):
            pass

    class FakeBrowser:
        async def new_context(self):
            return FakeContext()
        async def close(self):
            pass
        async def new_page(self):
            return FakePage()

    class FakePW:
        chromium = None

        async def __aenter__(self):
            self.chromium = type("FakeChromium", (), {
                "launch": mocker.AsyncMock(return_value=FakeBrowser())
            })()
            return self

        async def __aexit__(self, *args):
            pass

    mocker.patch("playwright.async_api.async_playwright", return_value=FakePW())

    disk = QuarkDisk()
    cookie = await disk.login_via_browser(timeout=5)
    assert "__pus=pus_val" in cookie
    assert disk.is_cookie_set
    # Should have parsed the cookie
    assert disk._cookie_parsed.get("__pus") == "pus_val"


@pytest.mark.asyncio
async def test_login_via_browser_timeout(mocker):
    """Timeout when cookies never appear."""
    from cloud_disk.kuake import QuarkDisk

    class FakeContext:
        async def new_page(self):
            return FakePage()
        async def cookies(self):
            return [{"name": "wrong", "value": "x"}]

    class FakePage:
        async def goto(self, url):
            pass

    class FakeBrowser:
        async def new_context(self):
            return FakeContext()
        async def close(self):
            pass
        async def new_page(self):
            return FakePage()

    class FakePW:
        async def __aenter__(self):
            self.chromium = type("FakeChromium", (), {
                "launch": mocker.AsyncMock(return_value=FakeBrowser())
            })()
            return self
        async def __aexit__(self, *args):
            pass

    mocker.patch("playwright.async_api.async_playwright", return_value=FakePW())

    disk = QuarkDisk()
    with pytest.raises(CookieExpiredError, match="timed out"):
        await disk.login_via_browser(timeout=2)


# ===========================================================================
# Parallel download tests
# ===========================================================================

@pytest.mark.asyncio
async def test_download_parallel_two_segments(disk, mocker, tmp_path):
    dest = tmp_path / "parallel.nsp"
    seg0 = b"A" * 300000
    seg1 = b"B" * 300000

    mocker.patch.object(disk, "get_download_link",
                        return_value="https://dl.quark.cn/parallel")
    mocker.patch.object(disk, "_probe_download",
                        return_value=(600000, True))
    mocker.patch.object(disk, "_get_download_stream_headers",
                        return_value={"Accept": "*/*"})

    class SegStream:
        def __init__(self, data, status=206):
            self.status_code = status
            self.headers = {"Content-Length": str(len(data))}
            self._data = data
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def aiter_bytes(self, chunk_size=1024):
            yield self._data

    streams = [SegStream(seg0), SegStream(seg1)]
    call_idx = [0]

    class ClientForSeg:
        async def aclose(self): pass
        def stream(self, method, url, headers):
            i = call_idx[0]
            call_idx[0] += 1
            return streams[i]

    mocker.patch(
        "cloud_disk.base.httpx.AsyncClient",
        side_effect=lambda *a, **kw: ClientForSeg(),
    )

    result = await disk.download("fid_001", str(dest), segments=2)
    assert result == str(dest.absolute())
    assert dest.stat().st_size == 600000
    assert dest.read_bytes() == seg0 + seg1

@pytest.mark.asyncio
async def test_download_parallel_fallback_no_range(disk, mocker, tmp_path):
    """When Range not supported, falls back to sequential."""
    dest = tmp_path / "fallback.nsp"
    test_data = b"X" * 3000

    mocker.patch.object(disk, "get_download_link",
                        return_value="https://dl.quark.cn/norange")

    # Probe reports no Range support
    mocker.patch.object(disk, "_probe_download",
                        return_value=(3000, False))

    # Sequential download mock
    mocker.patch.object(disk, "_get_download_stream_headers",
                        return_value={"Accept": "*/*"})

    class FakeSeqStream:
        status_code = 200
        headers = {"Content-Length": "3000"}
        _data = test_data

        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def aiter_bytes(self, chunk_size=1024):
            yield self._data

    class FakeSC:
        def __init__(self, *a, **kw):
            pass
        def stream(self, method, url, headers):
            return FakeSeqStream()
        async def aclose(self):
            pass

    mocker.patch("cloud_disk.base.httpx.AsyncClient",
                 side_effect=lambda *a, **kw: FakeSC(*a, **kw))

    result = await disk.download("fid_001", str(dest), segments=8)
    assert dest.stat().st_size == 3000

# ===========================================================================
# login_via_browser — Baidu / Aliyun cookie detection
# ===========================================================================

@pytest.mark.asyncio
async def test_baidu_login_detects_bduss(mocker):
    """Baidu login detects BDUSS cookie."""
    from cloud_disk.baidu import BaiduDisk

    class FakeContext:
        async def new_page(self):
            return FakePage()
        async def cookies(self):
            return [{"name": "BDUSS", "value": "bduss_test"}]
    class FakePage:
        async def goto(self, url):
            pass
    class FakeBrowser:
        async def new_context(self):
            return FakeContext()
        async def close(self):
            pass
        async def new_page(self):
            return FakePage()
    class FakePW:
        async def __aenter__(self):
            self.chromium = type("FakeCh", (), {"launch": mocker.AsyncMock(return_value=FakeBrowser())})()
            return self
        async def __aexit__(self, *args):
            pass

    mocker.patch("playwright.async_api.async_playwright", return_value=FakePW())
    disk = BaiduDisk()
    cookie = await disk.login_via_browser(timeout=5)
    assert "BDUSS=bduss_test" in cookie


@pytest.mark.asyncio
async def test_aliyun_login_detects_refresh_token(mocker):
    """Aliyun login detects refresh_token cookie."""
    from cloud_disk.aliyun import AliyunDisk

    class FakeContext:
        async def new_page(self):
            return FakePage()
        async def cookies(self):
            return [{"name": "refresh_token", "value": "rt_test_val"}]
    class FakePage:
        async def goto(self, url):
            pass
    class FakeBrowser:
        async def new_context(self):
            return FakeContext()
        async def close(self):
            pass
        async def new_page(self):
            return FakePage()
    class FakePW:
        async def __aenter__(self):
            self.chromium = type("FakeCh", (), {"launch": mocker.AsyncMock(return_value=FakeBrowser())})()
            return self
        async def __aexit__(self, *args):
            pass

    mocker.patch("playwright.async_api.async_playwright", return_value=FakePW())
    disk = AliyunDisk()
    cookie = await disk.login_via_browser(timeout=5)
    assert "refresh_token=rt_test_val" in cookie
