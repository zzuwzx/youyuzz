"""cloud_disk.baidu: Baidu Netdisk (Lf'Lf|Lf'Lf+) provider.

Implements the CloudDiskBase contract for Baidu Wangpan cookie-based API.

Usage::

    from cloud_disk.baidu import BaiduDisk
    disk = BaiduDisk()
    await disk.login_via_browser()
    task = await disk.save_to_drive("https://pan.baidu.com/s/1abcd")
    await disk.download(task.file_id, "C:/downloads/game.nsp", segments=8)
"""

from __future__ import annotations

import hashlib
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

BAIDU_PAN_HOST = "pan.baidu.com"
BAIDU_BASE = f"https://{BAIDU_PAN_HOST}"

SHARE_URL_RE = re.compile(
    r"(?:https?://)?pan\.baidu\.com/"
    r"(?:s/1([a-zA-Z0-9_-]+)|share/init\?surl=([a-zA-Z0-9_-]+))",
    re.IGNORECASE,
)
REQUIRED_COOKIE_KEYS = ("BDUSS",)
API_USER_INFO      = "/api/user/info"
API_SHARE_INIT     = "/share/init"
API_SHARE_VERIFY   = "/share/verify"
API_SHARE_LIST     = "/share/wxlist"
API_SHARE_TRANSFER = "/share/transfer"
API_FILE_DOWNLOAD  = "/api/download"

BAIDU_APP_ID     = "250528"
BAIDU_CLIENTTYPE = "12"
BAIDU_CHANNEL    = "chunlei"

BDSTOKEN_RE = re.compile(r'"bdstoken"\s*:\s*"([^"]+)"', re.IGNORECASE)
LOGID_RE    = re.compile(r'"logid"\s*:\s*"([^"]+)"', re.IGNORECASE)
SHAREID_RE  = re.compile(r'"shareid"\s*:\s*"?(\d+)"?', re.IGNORECASE)
UK_RE       = re.compile(r'"uk"\s*:\s*"?(\d+)"?', re.IGNORECASE)


class BaiduDisk(CloudDiskBase):
    """Baidu Netdisk provider."""

    # ---- Provider identity -----------------------------------------------
    LOGIN_URL = "https://pan.baidu.com/"
    _LOGIN_COOKIE_KEYS = {"BDUSS"}

    # ---- Download tuning --------------------------------------------------
    _DOWNLOAD_CONNECT_TIMEOUT = 15.0
    _DOWNLOAD_READ_TIMEOUT = 300.0

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._bdstoken: str = ""
        self._share_info_cache: dict[str, dict] = {}

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BAIDU_BASE,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._bdstoken = ""
        self._share_info_cache.clear()

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
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
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        headers_extra: Optional[dict] = None,
        expect_json: bool = True,
    ) -> dict | str:
        client = await self._ensure_client()
        try:
            resp = await client.request(
                method=method, url=path, params=params, data=data,
                headers=self._headers(headers_extra),
            )
        except httpx.TimeoutException:
            raise RateLimitedError(DiskType.BAIDU, retry_after=30)
        if resp.status_code == 429:
            raise RateLimitedError(DiskType.BAIDU, retry_after=int(resp.headers.get("Retry-After", 60)))
        if resp.status_code >= 500:
            raise RateLimitedError(DiskType.BAIDU, retry_after=60)
        if expect_json and "application/json" in resp.headers.get("content-type", ""):
            data_j = resp.json()
            errno = data_j.get("errno", 0)
            if errno in (-6, -9, 2, 111, 110):
                raise CookieExpiredError(DiskType.BAIDU, f"Baidu API error (errno={errno})")
            if errno != 0 and errno is not None:
                logger.warning("Baidu API errno=%s: %s", errno, data_j.get("errmsg", ""))
            return data_j
        if resp.status_code in (301, 302):
            if "login" in resp.headers.get("location", "").lower():
                raise CookieExpiredError(DiskType.BAIDU)
        if resp.status_code in (401, 403):
            raise CookieExpiredError(DiskType.BAIDU)
        if not resp.is_success and expect_json:
            raise RuntimeError(f"Baidu HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.text if not expect_json else resp.json()

    async def _fetch_bdstoken(self) -> str:
        if self._bdstoken:
            return self._bdstoken
        for key in ("BDSTOKEN", "bdstoken"):
            if key in self._cookie_parsed:
                self._bdstoken = self._cookie_parsed[key]
                return self._bdstoken
        try:
            data = await self._request("GET", API_USER_INFO)
            token = data.get("bdstoken", "")
            if token:
                self._bdstoken = token
                return token
        except Exception:
            pass
        try:
            client = await self._ensure_client()
            resp = await client.get(f"{BAIDU_BASE}/disk/home", headers=self._headers({"Accept": "text/html"}))
            m = BDSTOKEN_RE.search(resp.text)
            if m:
                self._bdstoken = m.group(1)
                return self._bdstoken
        except Exception:
            pass
        raise CookieExpiredError(DiskType.BAIDU, "Cannot extract bdstoken")

    # ------------------------------------------------------------------
    # Cookie validation
    # ------------------------------------------------------------------

    async def validate_cookie(self) -> bool:
        if not self._cookie:
            raise CookieExpiredError(DiskType.BAIDU, "No cookie set")
        if not any(k in self._cookie_parsed for k in REQUIRED_COOKIE_KEYS):
            raise CookieExpiredError(DiskType.BAIDU, "Cookie missing BDUSS")
        data = await self._request("GET", API_USER_INFO)
        uk = data.get("uk", data.get("user_info", {}).get("uk"))
        if not uk and not data.get("records"):
            raise CookieExpiredError(DiskType.BAIDU, "No user identity in response")
        self._bdstoken = data.get("bdstoken", "")
        logger.info("Baidu cookie validated, uk=%s", uk)
        return True

    # ------------------------------------------------------------------
    # Share parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_surl(share_url: str) -> str:
        m = SHARE_URL_RE.search(share_url)
        if not m:
            raise ValueError(f"Not a valid Baidu share URL: {share_url}")
        return m.group(1) or m.group(2)

    async def _get_share_info(self, surl: str, passcode: str = "") -> dict:
        if surl in self._share_info_cache:
            return self._share_info_cache[surl]
        try:
            text = await self._request("GET", f"{API_SHARE_INIT}?surl={surl}", expect_json=False)
        except Exception:
            raise ValueError(f"Cannot access share: {surl}")
        if "initPasswd" in text:
            if not passcode:
                raise ValueError(f"Share requires a passcode: {surl}")
            ts = int(time.time() * 1000)
            await self._request("POST",
                f"{API_SHARE_VERIFY}?surl={surl}&t={ts}&channel={BAIDU_CHANNEL}&clienttype=0&web=1",
                data={"pwd": passcode},
                headers_extra={"Content-Type": "application/x-www-form-urlencoded"})
        info: dict = {"surl": surl}
        for key, pattern in [("shareid", SHAREID_RE), ("uk", UK_RE),
                              ("bdstoken", BDSTOKEN_RE), ("logid", LOGID_RE)]:
            m = pattern.search(text)
            if m:
                info[key] = m.group(1)
        if "shareid" not in info or "uk" not in info:
            raise ValueError(f"Cannot extract share metadata from page (surl={surl})")
        self._share_info_cache[surl] = info
        return info

    async def _list_share_files(self, shareid: str, uk: str, bdstoken: str) -> list[dict]:
        all_files: list[dict] = []
        page = 1
        while True:
            data = await self._request("GET", API_SHARE_LIST, params={
                "channel": "weixin", "version": "2.2.2", "clienttype": "25", "web": "1",
                "shareid": shareid, "uk": uk, "dir": "/",
                "order": "time", "desc": "1", "page": str(page), "num": "100",
            })
            records = data.get("records", data.get("list", []))
            if not records:
                break
            for f in records:
                all_files.append({
                    "fs_id": str(f.get("fs_id", "")),
                    "server_filename": f.get("server_filename", f.get("filename", "")),
                    "size": f.get("size", 0), "isdir": f.get("isdir", 0),
                    "path": f.get("path", "/"), "category": f.get("category", 0),
                })
            if len(records) < 100:
                break
            page += 1
        return all_files

    # ------------------------------------------------------------------
    # save_to_drive
    # ------------------------------------------------------------------

    async def save_to_drive(
        self, share_url: str, passcode: str = "", target_dir_id: str = "",
    ) -> TransferTask:
        surl = self._extract_surl(share_url)
        info = await self._get_share_info(surl, passcode)
        shareid, uk = info["shareid"], info["uk"]
        bdstoken = info.get("bdstoken", "") or await self._fetch_bdstoken()
        files = await self._list_share_files(shareid, uk, bdstoken)
        if not files:
            raise ValueError(f"No files found in share: {share_url}")
        target = next((f for f in files if not f["isdir"]), files[0])
        dest_path = target_dir_id or "/"
        await self._request("POST", API_SHARE_TRANSFER, params={
            "shareid": shareid, "from": uk, "bdstoken": bdstoken,
            "channel": BAIDU_CHANNEL, "clienttype": "0", "web": "1",
            "t": str(int(time.time() * 1000)),
        }, data={"fsidlist": f'[{target["fs_id"]}]', "path": dest_path},
           headers_extra={"Content-Type": "application/x-www-form-urlencoded"})
        logger.info("Transferred '%s' to Baidu drive", target["server_filename"])
        return TransferTask(
            disk_type=DiskType.BAIDU, share_id=surl,
            file_name=target["server_filename"], file_id=target["fs_id"],
            size_bytes=target["size"], is_dir=bool(target["isdir"]),
            parent_id=dest_path,
        )

    # ------------------------------------------------------------------
    # get_download_link
    # ------------------------------------------------------------------

    async def get_download_link(self, file_id: str) -> str:
        bdstoken = await self._fetch_bdstoken()
        ts = int(time.time())
        fidlist = f"[{file_id}]"
        sign_raw = (
            f"app_id={BAIDU_APP_ID}&channel={BAIDU_CHANNEL}&clienttype={BAIDU_CLIENTTYPE}"
            f"&web=1&bdstoken={bdstoken}&fidlist={fidlist}&type=dlink&timestamp={ts}"
        )
        sign = hashlib.md5(sign_raw.encode()).hexdigest()
        data = await self._request("GET", API_FILE_DOWNLOAD, params={
            "app_id": BAIDU_APP_ID, "channel": BAIDU_CHANNEL,
            "clienttype": BAIDU_CLIENTTYPE, "web": "1",
            "bdstoken": bdstoken, "fidlist": fidlist, "type": "dlink",
            "timestamp": str(ts), "sign": sign,
        })
        dlinks = data.get("dlink", [])
        if not dlinks:
            raise ValueError(f"No download link for file_id={file_id}")
        dlink = dlinks[0].get("dlink", "")
        if not dlink:
            raise ValueError(f"Empty dlink for file_id={file_id}")
        return dlink

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
        return {"surl": m.group(1) or m.group(2)}

    @staticmethod
    def is_my_url(url: str) -> bool:
        return SHARE_URL_RE.search(url) is not None
