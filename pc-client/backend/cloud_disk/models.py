"""cloud_disk: Data models for cloud disk integration.

Defines shared types used across all disk providers:
  - DiskType: enum for supported cloud disk providers
  - CloudDiskLink: parsed disk share link
  - TransferTask: result of a save-to-drive operation
  - DownloadProgress: real-time download progress callback type
  - CookieExpiredError: raised when cookie is invalid
  - RateLimitedError: raised when hitting rate limits
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional


class DiskType(str, enum.Enum):
    """Supported cloud disk provider types."""
    QUARK = "quark"       # 夸克网盘
    BAIDU = "baidu"       # 百度网盘 (Phase 4)
    ALIYUN = "aliyun"     # 阿里云盘 (Phase 4)

    def __str__(self) -> str:
        return self.value


@dataclass
class CloudDiskLink:
    """Parsed representation of a cloud disk share link.

    Example:
        URL: https://pan.quark.cn/s/abc123#/list/share/xxx
        => disk_type=QUARK, share_id="abc123", file_id="xxx"
    """
    disk_type: DiskType
    raw_url: str
    share_id: str                    # e.g. "abc123" from pan.quark.cn/s/abc123
    file_id: Optional[str] = None    # specific file within share
    passcode: Optional[str] = None   # extraction code, if any


@dataclass
class TransferTask:
    """Result of saving a shared file to the user's own cloud drive."""
    disk_type: DiskType
    share_id: str
    file_name: str
    file_id: str            # ID in user's drive after saving
    size_bytes: int = 0
    is_dir: bool = False
    parent_id: str = ""     # parent directory ID in user's drive


@dataclass
class DownloadTask:
    """Ongoing or completed download task metadata."""
    disk_type: DiskType
    file_name: str
    file_id: str
    dest_path: str          # local filesystem path
    total_bytes: int = 0
    downloaded_bytes: int = 0
    is_complete: bool = False
    error: Optional[str] = None


#: Callback signature for download progress reporting.
#: Receives (downloaded_bytes, total_bytes, file_name).
DownloadProgressCallback = Callable[[int, int, str], Awaitable[None]]


class CookieExpiredError(Exception):
    """Raised when the stored cookie is expired or invalid.

    The caller should prompt the user to re-login and update the cookie.
    """
    def __init__(self, disk_type: DiskType, message: str = ""):
        self.disk_type = disk_type
        super().__init__(message or f"{disk_type.value} cookie has expired or is invalid")


class RateLimitedError(Exception):
    """Raised when the cloud disk API returns a rate-limit or block response."""
    def __init__(self, disk_type: DiskType, retry_after: int = 60):
        self.disk_type = disk_type
        self.retry_after = retry_after
        super().__init__(
            f"{disk_type.value} rate-limited, retry after {retry_after}s"
        )


class LinkExpiredError(Exception):
    """Raised when a download link has expired and needs refresh."""
    def __init__(self, disk_type: DiskType, file_name: str):
        self.disk_type = disk_type
        self.file_name = file_name
        super().__init__(
            f"Download link for '{file_name}' on {disk_type.value} has expired"
        )
