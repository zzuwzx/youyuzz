"""cloud_disk.kuake: Quark cloud disk (LfusLf¬Lf") provider.

Implements the CloudDiskBase contract for Quark cookie-based API.

Usage::

    from cloud_disk.kuake import QuarkDisk

    disk = QuarkDisk()
    await disk.login_via_browser()       # QR code login
    await disk.save_to_drive("https://pan.quark.cn/s/abc123")
    await disk.download(task.file_id, "C:/downloads/game.nsp", segments=4)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from .base import CloudDiskBase
from .models import (
    DiskType,
    TransferTask,
    CookieExpiredError,
    RateLimitedError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Quark API constants
# ---------------------------------------------------------------------------

QUARK_HOST = "drive-pc.quark.cn"
QUARK_BASE = f"https://{QUARK_HOST}"
QUARK_ORIGIN = "https://pan.quark.cn"
QUARK_REFERER = f"{QUARK_ORIGIN}/"

API_USER_CONFIG   = "/1/clouddrive/config"
API_SHARE_TOKEN   = "/1/clouddrive/share/sharepage/token"
API_SHARE_DETAIL  = "/1/clouddrive/share/sharepage/token"
API_SHARE_SAVE    = "/1/clouddrive/share/sharepage/save"
API_FILE_DOWNLOAD = "/1/clouddrive/file/download"

COMMON_QUERY = "?pr=ucpro&fr=pc&uc_param_str="
REQUIRED_COOKIE_KEY = "__pus"
SHARE_URL_RE = re.compile(
    r"(?:https?://)?pan\.quark\.cn/s/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)


class QuarkDisk(CloudDiskBase):
    """Quark cloud disk provider."""

    # ---- Provider identity -----------------------------------------------
    LOGIN_URL = "https://pan.quark.cn/"
    _LOGIN_COOKIE_KEYS = {"__pus"}

    # ---- Download tuning --------------------------------------------------
    _DOWNLOAD_CONNECT_TIMEOUT = 10.0
    _DOWNLOAD_READ_TIMEOUT = 120.0

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._share_tokens: dict[str, str] = {}
        self._share_files: dict[str, list[dict]] = {}

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=QUARK_BASE,
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"Origin": QUARK_ORIGIN, "Referer": QUARK_REFERER},
                follow_redirects=False,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._share_tokens.clear()
        self._share_files.clear()

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        if self._cookie:
            h["Cookie"] = self._cookie
        if extra:
            h.update(extra)
        return h

    async def _request(
        self, method: str, path: str, *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        headers_extra: Optional[dict] = None,
    ) -> dict:
        client = await self._ensure_client()
        try:
            resp = await client.request(
                method=method, url=path,
                json=json_body, params=params,
                headers=self._headers(headers_extra),
            )
        except httpx.TimeoutException:
            raise RateLimitedError(DiskType.QUARK, retry_after=30)

        if resp.status_code == 401:
            raise CookieExpiredError(DiskType.QUARK)
        if resp.status_code in (301, 302):
            location = resp.headers.get("location", "")
            if "login" in location.lower() or "passport" in location.lower():
                raise CookieExpiredError(DiskType.QUARK)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise RateLimitedError(DiskType.QUARK, retry_after=retry_after)
        if resp.status_code >= 500:
            raise RateLimitedError(DiskType.QUARK, retry_after=60)

        data = resp.json()
        if not resp.is_success:
            msg = data.get("message", data.get("msg", str(resp.status_code)))
            code = data.get("code", -1)
            logger.warning("Quark API error [%s] %s: %s", code, path, msg)
            if code in (-100, -2011):
                raise CookieExpiredError(DiskType.QUARK)
            raise RuntimeError(f"Quark API error ({code}): {msg}")
        return data

    # ------------------------------------------------------------------
    # Cookie validation
    # ------------------------------------------------------------------

    async def validate_cookie(self) -> bool:
        if not self._cookie:
            raise CookieExpiredError(DiskType.QUARK, "No cookie set")
        if REQUIRED_COOKIE_KEY not in self._cookie_parsed:
            raise CookieExpiredError(DiskType.QUARK, f"Cookie missing required key: {REQUIRED_COOKIE_KEY}")

        path = f"{API_USER_CONFIG}{COMMON_QUERY}"
        data = await self._request("GET", path)
        result = data.get("data", {})
        nickname = result.get("nickname", "")
        if not nickname:
            raise CookieExpiredError(DiskType.QUARK, "No user identity in response")

        logger.info("Quark cookie validated for user: %s", nickname)
        return True

    # ------------------------------------------------------------------
    # Share info & file listing
    # ------------------------------------------------------------------

    async def _get_share_token(self, pwd_id: str, passcode: str = "") -> str:
        if pwd_id in self._share_tokens:
            return self._share_tokens[pwd_id]
        path = f"{API_SHARE_TOKEN}{COMMON_QUERY}"
        data = await self._request("POST", path, json_body={"pwd_id": pwd_id, "passcode": passcode})
        stoken = data.get("data", {}).get("stoken", "")
        if not stoken:
            raise ValueError(f"Failed to get share token for pwd_id={pwd_id}")
        self._share_tokens[pwd_id] = stoken
        return stoken

    async def _get_share_files(self, pwd_id: str, stoken: str) -> list[dict]:
        if pwd_id in self._share_files:
            return self._share_files[pwd_id]
        all_files: list[dict] = []
        page = 1
        self._share_title = ""
        while True:
            path = (
                f"{API_SHARE_DETAIL}{COMMON_QUERY}"
                f"&pwd_id={pwd_id}&stoken={stoken}"
                f"&pdir_fid=0&_page={page}&_size=100"
                f"&_sort=file_type:asc,updated_at:desc"
            )
            data = await self._request("GET", path)
            result = data.get("data", {})
            if not self._share_title:
                self._share_title = result.get("title", "")
            batch = result.get("list", [])
            if not batch:
                break
            for f in batch:
                all_files.append({
                    "fid": f.get("fid", ""),
                    "file_name": f.get("file_name", ""),
                    "size": f.get("size", 0),
                    "dir": f.get("dir", False),
                    "fid_token": f.get("share_fid_token", ""),
                    "pdir_fid": f.get("pdir_fid", "0"),
                })
            if len(batch) < 100:
                break
            page += 1
        self._share_files[pwd_id] = all_files
        return all_files

    # ------------------------------------------------------------------
    # save_to_drive
    # ------------------------------------------------------------------

    async def save_to_drive(
        self, share_url: str, passcode: str = "", target_dir_id: str = "",
    ) -> TransferTask:
        pwd_id = self._extract_pwd_id(share_url)
        stoken = await self._get_share_token(pwd_id, passcode)
        files = await self._get_share_files(pwd_id, stoken)
        if not files:
            raise ValueError(f"No files found in share: {share_url}")
        target = next((f for f in files if not f["dir"]), files[0])
        return await self._save_file(pwd_id, stoken, target, target_dir_id or "0")

    async def save_share_file(
        self, share_url: str, file_index: int = 0,
        passcode: str = "", target_dir_id: str = "",
    ) -> TransferTask:
        pwd_id = self._extract_pwd_id(share_url)
        stoken = await self._get_share_token(pwd_id, passcode)
        files = await self._get_share_files(pwd_id, stoken)
        if not files or file_index >= len(files):
            raise IndexError(f"File index {file_index} out of range (0-{len(files) - 1})")
        return await self._save_file(pwd_id, stoken, files[file_index], target_dir_id or "0")

    async def _save_file(
        self, pwd_id: str, stoken: str, file_info: dict, to_pdir_fid: str,
    ) -> TransferTask:
        path = f"{API_SHARE_SAVE}{COMMON_QUERY}"
        body = {
            "fid_list": [file_info["fid"]],
            "fid_token_list": [file_info["fid_token"]],
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id, "stoken": stoken,
            "pdir_fid": file_info["pdir_fid"],
            "scene": "link",
        }
        data = await self._request("POST", path, json_body=body)
        logger.info("Saved '%s' to drive (task_id=%s)", file_info["file_name"],
                     data.get("data", {}).get("task_id", ""))
        return TransferTask(
            disk_type=DiskType.QUARK, share_id=pwd_id,
            file_name=file_info["file_name"], file_id=file_info["fid"],
            size_bytes=file_info.get("size", 0),
            is_dir=file_info.get("dir", False),
            parent_id=to_pdir_fid,
        )

    # ------------------------------------------------------------------
    # get_download_link
    # ------------------------------------------------------------------

    async def get_download_link(self, file_id: str) -> str:
        path = f"{API_FILE_DOWNLOAD}{COMMON_QUERY}"
        data = await self._request("POST", path, json_body={"fids": [file_id]})
        files = data.get("data", [])
        if not files:
            raise ValueError(f"No download info for file_id={file_id}")
        download_url = files[0].get("download_url", "")
        if not download_url:
            raise ValueError(f"Empty download URL for file_id={file_id}")
        return download_url

    # ------------------------------------------------------------------
    # Download headers (override base)
    # ------------------------------------------------------------------

    def _get_download_stream_headers(self) -> dict:
        return self._headers({"Accept": "*/*"})

    # ------------------------------------------------------------------
    # Static utilities
    # ------------------------------------------------------------------

    @staticmethod
    def parse_share_url(url: str) -> Optional[dict]:
        m = SHARE_URL_RE.search(url)
        if not m:
            return None
        return {"pwd_id": m.group(1)}

    @staticmethod
    def is_my_url(url: str) -> bool:
        return SHARE_URL_RE.search(url) is not None

    @staticmethod
    def _extract_pwd_id(share_url: str) -> str:
        m = SHARE_URL_RE.search(share_url)
        if not m:
            raise ValueError(f"Not a valid Quark share URL: {share_url}")
        return m.group(1)
