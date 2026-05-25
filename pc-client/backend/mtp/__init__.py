"""
MTP 传输模块 — pc-client/backend/mtp/

提供统一的 MTPTransfer 抽象层，支持两种后端:
  - ShellCopyHereBackend    — Phase 1 快速上线 (win32com Shell)
  - IFileOperationBackend   — Phase 1 后期 (ctypes vtable 真实进度)

用法:
    from backend.mtp import ShellCopyHereBackend, PartitionType

    backend = ShellCopyHereBackend()
    if backend.is_device_connected():
        backend.copy_file("game.nsp", PartitionType.SD_CARD, on_progress=my_cb)
"""

from .base import (
    MTPTransfer,
    PartitionType,
    PartitionInfo,
    CopyResult,
    TransferProgress,
    TransferItem,
    ProgressCallback,
)

from .shell_copy_here import ShellCopyHereBackend
from .wpd_backend import WpdBackend
from . import transfer_worker
from .ifile_operation import IFileOperationBackend
from .dbi_discovery import (
    find_switch_device,
    discover_partitions,
    DBIDiscoveryError,
)

__all__ = [
    # 抽象基类
    "MTPTransfer",
    # 数据类
    "PartitionType",
    "PartitionInfo",
    "CopyResult",
    "TransferProgress",
    "TransferItem",
    "ProgressCallback",
    # 后端实现
    "ShellCopyHereBackend",
    "WpdBackend",
    "IFileOperationBackend",
    # 设备发现工具
    "find_switch_device",
    "discover_partitions",
    "DBIDiscoveryError",
]
