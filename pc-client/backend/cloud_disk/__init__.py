"""cloud_disk: Cloud disk integration module.

Provides a unified interface across Quark, Baidu, and Aliyun cloud drives.

Quick start::

    from cloud_disk import QuarkDisk, DiskType

    disk = QuarkDisk()
    disk.set_cookie("__pus=xxx; ...")
    await disk.validate_cookie()
    task = await disk.save_to_drive("https://pan.quark.cn/s/abc123")
    await disk.download(task.file_id, "C:/downloads/game.nsp")

Provider factory::

    from cloud_disk import create_disk

    disk = create_disk(DiskType.QUARK)
    disk = create_disk(DiskType.BAIDU)   # raises NotImplementedError (Phase 4)
"""

from .models import (
    DiskType,
    CloudDiskLink,
    TransferTask,
    DownloadTask,
    DownloadProgressCallback,
    CookieExpiredError,
    RateLimitedError,
    LinkExpiredError,
)
from .base import CloudDiskBase
from .kuake import QuarkDisk
from .baidu import BaiduDisk
from .aliyun import AliyunDisk

__all__ = [
    # Models
    "DiskType",
    "CloudDiskLink",
    "TransferTask",
    "DownloadTask",
    "DownloadProgressCallback",
    "CookieExpiredError",
    "RateLimitedError",
    "LinkExpiredError",
    # Abstract
    "CloudDiskBase",
    # Providers
    "QuarkDisk",
    "BaiduDisk",
    "AliyunDisk",
    # Factory
    "create_disk",
]

# Provider registry
_PROVIDERS = {
    DiskType.QUARK: QuarkDisk,
    DiskType.BAIDU: BaiduDisk,
    DiskType.ALIYUN: AliyunDisk,
}


def create_disk(disk_type: DiskType) -> CloudDiskBase:
    """Factory: create a disk provider instance by type.

    Raises NotImplementedError for Phase 4 stubs.
    """
    cls = _PROVIDERS.get(disk_type)
    if cls is None:
        raise ValueError(f"Unknown disk type: {disk_type}")
    return cls()
