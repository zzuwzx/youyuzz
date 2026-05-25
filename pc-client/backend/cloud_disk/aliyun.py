"""cloud_disk.aliyun: Alibaba Cloud Drive (LfL'LfL'Lf|Lf) provider.

Supports cookie-based and refresh_token-based authentication.

Usage::

    from cloud_disk.aliyun import AliyunDisk
    disk = AliyunDisk()
    await disk.login_via_browser()
    task = await disk.save_to_drive("https://www.alipan.com/s/abc123")
    await disk.download(task.file_id, "C:/downloads/game.nsp", segments=4)
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

import httpx

from .base import CloudDiskBase
from .models import (
    DiskType, TransferTask, CookieExpiredError, RateLimitedError,
)

logger = logging.getLogger(__name__)

ALIYUN_API_HOST  = "api.aliyundrive.com"
ALIYUN_AUTH_HOST = "auth.aliyundrive.com"
ALIYUN_BASE      = f"https://{ALIYUN_API_HOST}"
ALIYUN_AUTH_BASE = f"https://{ALIYUN_AUTH_HOST}"
ALIYUN_ORIGIN    = "https://www.alipan.com"

SHARE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:aliyundrive|alipan)\.com/s/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)

API_AUTH_TOKEN    = "/v2/account/token"
API_USER_GET      = "/adrive/v2/user/get"
API_SHARE_TOKEN   = "/adrive/v2/share_link/get_share_token"
API_SHARE_LIST    = "/adrive/v2/file/list_by_share"
API_BATCH         = "/adrive/v3/batch"
API_FILE_DOWNLOAD = "/adrive/v2/file/get_download_url"


class AliyunDisk(CloudDiskBase):
    """Alibaba Cloud Drive provider."""

    # ---- Provider identity -----------------------------------------------
    LOGIN_URL = "https://www.alipan.com/"
    _LOGIN_COOKIE_KEYS = {"refresh_token"}

    # ---- Download tuning --------------------------------------------------
    _DOWNLOAD_CONNECT_TIMEOUT = 15.0
    _DOWNLOAD_READ_TIMEOUT = 300.0

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._auth_client: Optional[httpx.AsyncClient] = None
        self._access_token: str = ""
        self._refresh_token: str = ""
        self._token_expire_at: float = 0.0
        self._drive_id: str = ""
        self._user_id: str = ""

    def set_refresh_token(self, token: str) -> None:
        self._refresh_token = token.strip()

    async def _ensure_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expire_at - self.TOKEN_EXPIRE_BUFFER:
            return self._access_token
        if not self._refresh_token:
            for key in ("refresh_token", "RefreshToken"):
                if key in self._cookie_parsed:
                    self._refresh_token = self._cookie_parsed[key]
                    break
        if not self._refresh_token:
            raise CookieExpiredError(DiskType.ALIYUN, "No refresh_token found")
        auth = await self._ensure_auth_client()
        resp = await auth.post(API_AUTH_TOKEN,
            json={"refresh_token": self._refresh_token, "grant_type": "refresh_token"})
        if resp.status_code != 200:
            raise CookieExpiredError(DiskType.ALIYUN, f"Token refresh failed (HTTP {resp.status_code})")
        data = resp.json()
        self._access_token = data.get("access_token", "")
        expires_in = data.get("expires_in", 7200)
        self._token_expire_at = time.time() + expires_in
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._user_id = data.get("user_id", self._user_id)
        self._drive_id = data.get("default_drive_id", self._drive_id)
        if not self._access_token:
            raise CookieExpiredError(DiskType.ALIYUN, "Empty access_token in response")
        return self._access_token

    async def _ensure_auth_client(self) -> httpx.AsyncClient:
        if self._auth_client is None:
            self._auth_client = httpx.AsyncClient(
                base_url=ALIYUN_AUTH_BASE,
                timeout=httpx.Timeout(15.0, connect=10.0),
                headers={"Content-Type": "application/json"},
            )
        return self._auth_client

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=ALIYUN_BASE,
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"Origin": ALIYUN_ORIGIN, "Referer": f"{ALIYUN_ORIGIN}/"},
                follow_redirects=False,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._auth_client is not None:
            await self._auth_client.aclose()
            self._auth_client = None
        self._access_token = ""
        self._token_expire_at = 0.0

    async def _request(
        self, method: str, path: str, *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
    ) -> dict:
        token = await self._ensure_token()
        client = await self._ensure_client()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
        if extra_headers:
            headers.update(extra_headers)
        try:
            resp = await client.request(method=method, url=path, json=json_body, params=params, headers=headers)
        except httpx.TimeoutException:
            raise RateLimitedError(DiskType.ALIYUN, retry_after=30)
        if resp.status_code == 401:
            self._access_token = ""
            raise CookieExpiredError(DiskType.ALIYUN)
        if resp.status_code == 429:
            raise RateLimitedError(DiskType.ALIYUN, retry_after=int(resp.headers.get("Retry-After", 60)))
        if resp.status_code >= 500:
            raise RateLimitedError(DiskType.ALIYUN, retry_after=60)
        data = resp.json()
        code = data.get("code", "")
        if code and code != "Success" and code != "success":
            msg = data.get("message", str(code))
            logger.warning("Aliyun API error [%s]: %s", code, msg)
            if code in ("AccessTokenInvalid", "AccessTokenExpired", "UserNotLogin"):
                self._access_token = ""
                raise CookieExpiredError(DiskType.ALIYUN, msg)
            raise RuntimeError(f"Aliyun API error ({code}): {msg}")
        if not resp.is_success:
            raise RuntimeError(f"Aliyun HTTP {resp.status_code}")
        return data

    # ------------------------------------------------------------------
    # Cookie validation
    # ------------------------------------------------------------------

    async def validate_cookie(self) -> bool:
        if self._refresh_token:
            token = await self._ensure_token()
        elif not self._cookie:
            raise CookieExpiredError(DiskType.ALIYUN, "No cookie or refresh_token set")
        if not self._access_token:
            token = await self._ensure_token()
        data = await self._request("POST", API_USER_GET)
        user = data.get("user_name") or data.get("nick_name", "")
        if not user:
            raise CookieExpiredError(DiskType.ALIYUN, "No user identity in response")
        drive = data.get("default_drive_id", "")
        if drive:
            self._drive_id = drive
        uid = data.get("user_id", "")
        if uid:
            self._user_id = uid
        logger.info("Aliyun cookie validated for user: %s", user)
        return True

    # ------------------------------------------------------------------
    # Share helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_share_id(share_url: str) -> str:
        m = SHARE_URL_RE.search(share_url)
        if not m:
            raise ValueError(f"Not a valid Aliyun share URL: {share_url}")
        return m.group(1)

    async def _get_share_token(self, share_id: str, passcode: str = "") -> str:
        data = await self._request("POST", API_SHARE_TOKEN,
            json_body={"share_id": share_id, "share_pwd": passcode})
        token = data.get("share_token", "")
        if not token:
            raise ValueError(f"Failed to get share token for {share_id}")
        return token

    async def _list_share_files(self, share_id: str, share_token: str) -> list[dict]:
        all_files: list[dict] = []
        marker = ""
        while True:
            body: dict = {
                "share_id": share_id, "parent_file_id": "root",
                "limit": 100, "order_by": "name", "order_direction": "DESC",
            }
            if marker:
                body["marker"] = marker
            data = await self._request("POST", API_SHARE_LIST, json_body=body,
                extra_headers={"x-share-token": share_token})
            items = data.get("items", [])
            for f in items:
                all_files.append({
                    "file_id": f.get("file_id", ""), "name": f.get("name", ""),
                    "size": f.get("size", 0), "type": f.get("type", "file"),
                    "drive_id": f.get("drive_id", ""), "content_hash": f.get("content_hash", ""),
                })
            next_marker = data.get("next_marker", "")
            if not next_marker or not items:
                break
            marker = next_marker
        return all_files

    # ------------------------------------------------------------------
    # save_to_drive
    # ------------------------------------------------------------------

    async def save_to_drive(
        self, share_url: str, passcode: str = "", target_dir_id: str = "",
    ) -> TransferTask:
        share_id = self._extract_share_id(share_url)
        share_token = await self._get_share_token(share_id, passcode)
        files = await self._list_share_files(share_id, share_token)
        if not files:
            raise ValueError(f"No files found in share: {share_url}")
        target = next((f for f in files if f["type"] == "file"), files[0])
        dest_parent = target_dir_id or "root"
        body = {
            "requests": [{
                "body": {
                    "file_id": target["file_id"], "share_id": share_id,
                    "auto_rename": True, "to_parent_file_id": dest_parent,
                    "to_drive_id": self._drive_id,
                },
                "headers": {"Content-Type": "application/json"},
                "id": "0", "method": "POST", "url": "/file/copy",
            }],
            "resource": "file",
        }
        data = await self._request("POST", API_BATCH, json_body=body,
            extra_headers={"x-share-token": share_token})
        responses = data.get("responses", [])
        if not responses:
            raise RuntimeError("Batch copy returned no responses")
        result = responses[0]
        status = result.get("status", -1)
        if status not in (200, 201):
            err = result.get("body", {}).get("message", "unknown error")
            raise RuntimeError(f"Copy failed (status={status}): {err}")
        saved = result.get("body", {})
        file_id = saved.get("file_id", target["file_id"])
        logger.info("Saved '%s' to Aliyun Drive (file_id=%s)", target["name"], file_id)
        return TransferTask(
            disk_type=DiskType.ALIYUN, share_id=share_id,
            file_name=target["name"], file_id=file_id,
            size_bytes=target.get("size", 0),
            is_dir=(target["type"] == "folder"), parent_id=dest_parent,
        )

    # ------------------------------------------------------------------
    # get_download_link
    # ------------------------------------------------------------------

    async def get_download_link(self, file_id: str) -> str:
        data = await self._request("POST", API_FILE_DOWNLOAD,
            json_body={"drive_id": self._drive_id, "file_id": file_id})
        url = data.get("url", "")
        if not url:
            raise ValueError(f"No download URL for file_id={file_id}")
        return url

    # ------------------------------------------------------------------
    # Static utilities
    # ------------------------------------------------------------------

    @staticmethod
    def parse_share_url(url: str) -> Optional[dict]:
        m = SHARE_URL_RE.search(url)
        if not m:
            return None
        return {"share_id": m.group(1)}

    @staticmethod
    def is_my_url(url: str) -> bool:
        return SHARE_URL_RE.search(url) is not None
