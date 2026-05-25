"""cloud_disk.base: Abstract base class for cloud disk providers.

Every cloud disk provider (Quark, Baidu, Aliyun) must implement:

    validate_cookie()     — verify authentication
    save_to_drive()       — save shared file to user's drive
    get_download_link()   — get a direct download URL

The base class provides:

    login_via_browser()   — Playwright-based QR code login + cookie extraction
    download()            — single or multi-segment parallel download
    set_cookie()          — cookie management
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, ClassVar, Set

import httpx

from .models import (
    DiskType,
    TransferTask,
    DownloadProgressCallback,
    CookieExpiredError,
    RateLimitedError,
    LinkExpiredError,
)

logger = logging.getLogger(__name__)

# Files below this size always download in a single segment
MIN_SEGMENT_SIZE = 256 * 1024  # 256 KB (avoid splitting tiny files)


class CloudDiskBase(ABC):
    """Abstract base for all cloud disk providers.

    Subclass responsibilities:
      - Define LOGIN_URL, _LOGIN_COOKIE_KEYS
      - Implement validate_cookie(), save_to_drive(), get_download_link()
      - Optionally override _get_download_stream_headers() for custom headers

    Usage::

        disk = QuarkDisk()

        # Login via browser QR code (one-time)
        await disk.login_via_browser()

        # Save and download with multi-segment full speed
        task = await disk.save_to_drive("https://pan.quark.cn/s/abc123")
        await disk.download(
            task.file_id,
            dest_path="C:/downloads/game.nsp",
            segments=8,          # parallel segments for speed
            on_progress=my_callback,
        )
    """

    # ---- Provider identity (override in subclass) ---------------------------

    LOGIN_URL: ClassVar[str] = ""
    """Login page URL for browser-based QR code login."""

    _LOGIN_COOKIE_KEYS: ClassVar[Set[str]] = set()
    """Cookie names that must all be present after a successful login."""

    # ---- Download config (override in subclass) -----------------------------

    _DOWNLOAD_CONNECT_TIMEOUT: float = 15.0
    _DOWNLOAD_READ_TIMEOUT: float = 300.0

    # ---- Token expiry buffer (used by Aliyun token-based auth) --------------

    TOKEN_EXPIRE_BUFFER: int = 60

    # ------------------------------------------------------------------
    # Instance state
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._cookie: str = ""
        self._cookie_parsed: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Cookie management
    # ------------------------------------------------------------------

    @property
    def cookie(self) -> str:
        return self._cookie

    def set_cookie(self, cookie: str) -> None:
        self._cookie = cookie.strip()
        self._cookie_parsed = self._parse_cookie(cookie)

    @staticmethod
    def _parse_cookie(raw: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in raw.split(";"):
            item = item.strip()
            if "=" not in item:
                continue
            key, _, val = item.partition("=")
            result[key.strip()] = val.strip()
        return result

    @property
    def is_cookie_set(self) -> bool:
        return bool(self._cookie)

    # ------------------------------------------------------------------
    # Browser-based QR code login
    # ------------------------------------------------------------------

    async def login_via_browser(
        self,
        *,
        timeout: int = 120,
        headless: bool = False,
    ) -> str:
        """Open a browser to the login page for QR-code / phone scanning.

        Uses Playwright to launch a visible Chromium window, navigate to
        ``LOGIN_URL``, then poll for login completion.  Once the expected
        cookies appear (defined by ``_LOGIN_COOKIE_KEYS``), cookies are
        extracted and saved via ``set_cookie()``.

        Args:
            timeout: Maximum seconds to wait for the user to scan the QR code.
            headless: Run the browser in headless mode (default False —
                      user must see the QR code).

        Returns:
            The raw cookie string extracted from the browser.

        Raises:
            CookieExpiredError: if login did not complete within ``timeout``.
            RuntimeError: if Playwright or Chromium is not installed.
        """
        if not self.LOGIN_URL:
            raise RuntimeError(
                f"{type(self).__name__} does not define LOGIN_URL"
            )

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "playwright is required for login_via_browser(). "
                "Install with: pip install playwright && playwright install chromium"
            )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(self.LOGIN_URL)
            logger.info(
                "Browser opened at %s — scan the QR code with your phone "
                "(timeout: %ds)", self.LOGIN_URL, timeout,
            )

            start = time.monotonic()
            while time.monotonic() - start < timeout:
                cookies = await context.cookies()
                present_keys = {c["name"] for c in cookies}
                if self._LOGIN_COOKIE_KEYS and self._LOGIN_COOKIE_KEYS.issubset(present_keys):
                    logger.info("Login detected — %d cookies found", len(present_keys))
                    break
                await asyncio.sleep(1.5)
            else:
                await browser.close()
                raise CookieExpiredError(
                    self._disk_type(),
                    f"Login timed out after {timeout}s",
                )

            # Extract full cookie string
            all_cookies = await context.cookies()
            cookie_parts = [f"{c['name']}={c['value']}" for c in all_cookies]
            cookie_str = "; ".join(cookie_parts)

            self.set_cookie(cookie_str)
            await browser.close()

        logger.info("login_via_browser complete — cookie saved")
        return cookie_str

    # ------------------------------------------------------------------
    # Abstract core operations
    # ------------------------------------------------------------------

    @abstractmethod
    async def validate_cookie(self) -> bool:
        """Check whether the current cookie is still valid.

        Returns True on success, raises CookieExpiredError otherwise.
        """
        ...

    @abstractmethod
    async def save_to_drive(
        self,
        share_url: str,
        passcode: str = "",
        target_dir_id: str = "",
    ) -> TransferTask:
        """Save shared content to the user's cloud drive.

        Returns TransferTask with the saved file's metadata including file_id.
        """
        ...

    @abstractmethod
    async def get_download_link(self, file_id: str) -> str:
        """Get a direct download URL for a file in the user's drive."""
        ...

    # ------------------------------------------------------------------
    # Download (concrete — single / multi-segment)
    # ------------------------------------------------------------------

    async def download(
        self,
        file_id: str,
        dest_path: str,
        *,
        on_progress: Optional[DownloadProgressCallback] = None,
        resume: bool = False,
        segments: int = 1,
    ) -> str:
        """Download a file to local disk.

        When ``segments > 1``, the file is split into equal parts and
        downloaded in parallel using HTTP Range requests, then reassembled.
        This breaks per-connection speed limits (especially useful for
        Baidu Netdisk).

        Falls back to single-segment if:
          - The server doesn't advertise ``Accept-Ranges: bytes``.
          - The file is smaller than ``segments * MIN_SEGMENT_SIZE``.

        Args:
            file_id: File ID from TransferTask.
            dest_path: Local filesystem path.
            on_progress: Async callback(downloaded, total, file_name).
            resume: Resume from an existing partial file.
            segments: Number of parallel download segments.

        Returns:
            Absolute path to the downloaded file.
        """
        if segments <= 1:
            return await self._download_sequential(
                file_id, dest_path,
                on_progress=on_progress,
                resume=resume,
            )

        # Try parallel; fall back to sequential if Range not supported
        url = await self.get_download_link(file_id)

        try:
            total_size, supports_range = await self._probe_download(url)
        except Exception:
            total_size, supports_range = 0, False

        if not supports_range or total_size < MIN_SEGMENT_SIZE * segments:
            logger.info(
                "Falling back to sequential download "
                "(supports_range=%s, size=%d)", supports_range, total_size,
            )
            return await self._download_sequential(
                file_id, dest_path,
                on_progress=on_progress,
                resume=resume,
            )

        return await self._download_parallel(
            url, dest_path,
            total_size=total_size,
            segments=segments,
            on_progress=on_progress,
        )

    # ------------------------------------------------------------------
    # Sequential download
    # ------------------------------------------------------------------

    async def _download_sequential(
        self,
        file_id: str,
        dest_path: str,
        *,
        on_progress: Optional[DownloadProgressCallback] = None,
        resume: bool = False,
    ) -> str:
        """Single-stream download with optional resume."""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        offset: int = 0
        if resume and dest.exists():
            offset = dest.stat().st_size
            if offset <= 0:
                offset = 0
            else:
                logger.info("Resuming download from byte %d", offset)

        download_url = await self.get_download_link(file_id)
        file_name = dest.name

        stream_headers = self._get_download_stream_headers()
        if offset > 0:
            stream_headers["Range"] = f"bytes={offset}-"

        stream_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                self._DOWNLOAD_READ_TIMEOUT,
                connect=self._DOWNLOAD_CONNECT_TIMEOUT,
                read=self._DOWNLOAD_READ_TIMEOUT,
            ),
            follow_redirects=True,
        )

        try:
            async with stream_client.stream(
                "GET", download_url, headers=stream_headers,
            ) as resp:
                self._check_stream_response(resp, file_name, offset)

                total = self._calc_total_bytes(resp, offset)
                downloaded = offset

                mode = "ab" if offset > 0 else "wb"
                with open(dest, mode) as f:
                    last_cb_time = 0.0
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        if on_progress and (now - last_cb_time > 0.5):
                            await on_progress(downloaded, total, file_name)
                            last_cb_time = now

                if on_progress:
                    await on_progress(downloaded, total, file_name)

        except httpx.TimeoutException:
            raise RateLimitedError(self._disk_type(), retry_after=30)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise LinkExpiredError(self._disk_type(), file_name)
            raise
        finally:
            await stream_client.aclose()

        logger.info(
            "Downloaded '%s' to %s (%d bytes)", file_name, dest, downloaded,
        )
        return str(dest.absolute())

    # ------------------------------------------------------------------
    # Parallel segmented download
    # ------------------------------------------------------------------

    async def _download_parallel(
        self,
        url: str,
        dest_path: str,
        *,
        total_size: int,
        segments: int,
        on_progress: Optional[DownloadProgressCallback] = None,
    ) -> str:
        """Download a file in multiple parallel segments."""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        file_name = dest.name

        segment_size = total_size // segments
        progress_state = {"bytes": 0, "total": total_size, "last_ts": 0.0}
        _lock = asyncio.Lock()

        async def _seg_callback(delta: int) -> None:
            async with _lock:
                progress_state["bytes"] += delta
                now = time.monotonic()
                if on_progress and (now - progress_state["last_ts"] > 0.5):
                    await on_progress(
                        progress_state["bytes"],
                        progress_state["total"],
                        file_name,
                    )
                    progress_state["last_ts"] = now

        async def _fetch_segment(i: int) -> None:
            start = i * segment_size
            end = start + segment_size - 1 if i < segments - 1 else total_size - 1
            part_path = f"{dest_path}.part{i}"

            stream_headers = self._get_download_stream_headers()
            stream_headers["Range"] = f"bytes={start}-{end}"

            stream_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    self._DOWNLOAD_READ_TIMEOUT,
                    connect=self._DOWNLOAD_CONNECT_TIMEOUT,
                    read=self._DOWNLOAD_READ_TIMEOUT,
                ),
                follow_redirects=True,
            )

            try:
                async with stream_client.stream(
                    "GET", url, headers=stream_headers,
                ) as resp:
                    if resp.status_code not in (200, 206):
                        raise RuntimeError(
                            f"Segment {i} failed: HTTP {resp.status_code}"
                        )
                    with open(part_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                            f.write(chunk)
                            await _seg_callback(len(chunk))
            finally:
                await stream_client.aclose()

        # Launch all segments
        tasks = [
            asyncio.create_task(_fetch_segment(i))
            for i in range(segments)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                # Clean up partial files
                for j in range(segments):
                    try:
                        os.remove(f"{dest_path}.part{j}")
                    except OSError:
                        pass
                raise r

        # Reassemble
        with open(dest, "wb") as out:
            for i in range(segments):
                part_path = f"{dest_path}.part{i}"
                with open(part_path, "rb") as f:
                    out.write(f.read())
                os.remove(part_path)

        # Final progress
        if on_progress:
            await on_progress(total_size, total_size, file_name)

        logger.info(
            "Parallel download complete: '%s' (%d bytes, %d segments)",
            file_name, total_size, segments,
        )
        return str(dest.absolute())

    # ------------------------------------------------------------------
    # Download helpers (override in subclass if needed)
    # ------------------------------------------------------------------

    def _get_download_stream_headers(self) -> dict:
        """Return headers for the download streaming request.

        Override in subclass to inject provider-specific auth headers.
        Default: basic Accept + User-Agent.
        """
        return {
            "Accept": "*/*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

    @staticmethod
    async def _probe_download(url: str) -> tuple[int, bool]:
        """HEAD request to discover file size and Range support.

        Returns:
            (content_length, accepts_ranges).
        """
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=10.0),
            follow_redirects=True,
        ) as client:
            resp = await client.head(url)
            content_length = int(resp.headers.get("Content-Length", 0))
            accepts_ranges = resp.headers.get("Accept-Ranges", "").lower() == "bytes"
            return content_length, accepts_ranges

    @staticmethod
    def _check_stream_response(
        resp: httpx.Response,
        file_name: str,
        offset: int,
    ) -> None:
        """Validate streaming response status."""
        if offset > 0:
            if resp.status_code not in (200, 206):
                raise LinkExpiredError(DiskType.QUARK, file_name)
        else:
            if resp.status_code >= 400:
                if resp.status_code in (401, 403):
                    raise LinkExpiredError(DiskType.QUARK, file_name)
                raise RuntimeError(f"Download failed: HTTP {resp.status_code}")

    @staticmethod
    def _calc_total_bytes(resp: httpx.Response, offset: int) -> int:
        """Extract total byte count from response headers."""
        cl = resp.headers.get("Content-Length")
        if cl is not None:
            return int(cl) + offset
        cr = resp.headers.get("Content-Range", "")
        m = re.search(r"/(\d+)", cr)
        if m:
            return int(m.group(1))
        return 0

    # ------------------------------------------------------------------
    # Link parsing
    # ------------------------------------------------------------------

    @staticmethod
    @abstractmethod
    def parse_share_url(url: str) -> Optional[dict]:
        ...

    @staticmethod
    @abstractmethod
    def is_my_url(url: str) -> bool:
        ...

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _disk_type(self) -> DiskType:
        """Map subclass to DiskType enum."""
        name = type(self).__name__.lower()
        if "quark" in name:
            return DiskType.QUARK
        if "baidu" in name:
            return DiskType.BAIDU
        if "aliyun" in name:
            return DiskType.ALIYUN
        return DiskType.QUARK  # fallback
