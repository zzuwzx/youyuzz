"""
MTP 传输模块 — 抽象基类

定义 MTPTransfer 统一接口，所有后端必须实现此接口。
支持两种后端:
  - ShellCopyHereBackend    — win32com CopyHere(1556) + 阻尼进度模拟
  - IFileOperationBackend   — ctypes IFileOperation vtable + 原生进度回调
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import IntEnum, auto


class PartitionType(IntEnum):
    """DBI MTP 分区类型"""
    SD_CARD = 5      # TF 卡安装分区
    NAND = 6         # NAND/机身内存安装分区
    CHEATS = 0       # 金手指目录（如有）


class CopyResult(IntEnum):
    """传输结果状态码"""
    OK = 0
    DEVICE_NOT_FOUND = auto()
    PARTITION_NOT_FOUND = auto()
    NO_SPACE = auto()
    COPY_FAILED = auto()
    CANCELLED = auto()
    IO_ERROR = auto()


@dataclass
class PartitionInfo:
    """DBI 分区信息"""
    type: PartitionType
    name: str
    path: str                    # Shell namespace 路径，如 "5: SD Card install"
    free_bytes: int = 0
    total_bytes: int = 0

    @property
    def free_mb(self) -> float:
        return self.free_bytes / (1024 * 1024)

    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)

    @property
    def used_pct(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (1 - self.free_bytes / self.total_bytes) * 100


@dataclass
class TransferProgress:
    """单次传输进度快照"""
    bytes_total: int = 0
    bytes_done: int = 0
    ratio: float = 0.0          # 0.0 ~ 1.0
    elapsed_sec: float = 0.0
    eta_sec: float = -1.0       # -1 = 无法估算

    @property
    def pct(self) -> int:
        return int(self.ratio * 100)


@dataclass
class TransferItem:
    """单个传输任务"""
    source_path: str
    dest_partition: PartitionType = PartitionType.SD_CARD
    size_bytes: int = 0
    tag: str = ""                # 本体 / 升级 / DLC
    status: str = "pending"      # pending / transferring / completed / failed


ProgressCallback = Callable[[TransferProgress], None]


class MTPTransfer(ABC):
    """
    MTP 传输抽象基类。

    所有后端实现必须提供以下方法:
      - discover_partitions()  → DBI 分区发现
      - copy_file()            → 单文件传输（带进度回调）
      - get_free_space()       → 分区剩余空间查询
      - is_device_connected()  → 设备连接状态检查

    使用范例:
        backend = ShellCopyHereBackend()
        if backend.is_device_connected():
            partitions = backend.discover_partitions()
            backend.copy_file("game.nsp", PartitionType.SD_CARD, on_progress=my_callback)
    """

    # ---- 设备发现 ----

    @abstractmethod
    def is_device_connected(self) -> bool:
        """检查 Switch DBI MTP 设备是否已连接"""
        ...

    @abstractmethod
    def discover_partitions(self) -> dict[PartitionType, PartitionInfo]:
        """
        扫描 DBI MTP 分区并返回结构化信息。

        Returns:
            {PartitionType: PartitionInfo} 映射表。
            至少包含 PartitionType.SD_CARD 和 PartitionType.NAND。
        """
        ...

    # ---- 文件传输 ----

    @abstractmethod
    def copy_file(
        self,
        source: str,
        partition: PartitionType = PartitionType.SD_CARD,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> CopyResult:
        """
        传输单个文件到指定 DBI 分区。

        Args:
            source:      本地文件绝对路径
            partition:   目标分区（默认 SD_CARD）
            on_progress: 进度回调，每秒约 30 次；传 None 则静默传输

        Returns:
            CopyResult 状态码。
        """
        ...

    # ---- 存储查询 ----

    @abstractmethod
    def get_free_space(self, partition: PartitionType) -> int:
        """
        查询指定分区的剩余空间（字节）。

        Args:
            partition: 目标分区

        Returns:
            剩余字节数；分区不可用时返回 -1。
        """
        ...

    # ---- 分区自动选择 ----

    def select_partition(self, file_size_bytes: int) -> PartitionType:
        """
        根据文件大小自动选择最优安装分区。

        规则:
          1. 优先 TF 卡 (SD_CARD)
          2. TF 卡空间不足时回落 NAND

        Args:
            file_size_bytes: 待传输文件大小

        Returns:
            推荐的 PartitionType。
        """
        partitions = self.discover_partitions()
        sd = partitions.get(PartitionType.SD_CARD)
        nand = partitions.get(PartitionType.NAND)

        if sd and sd.free_bytes >= file_size_bytes:
            return PartitionType.SD_CARD
        if nand and nand.free_bytes >= file_size_bytes:
            return PartitionType.NAND

        # 两个分区都不够——仍返回 SD_CARD，由上层处理 NO_SPACE
        return PartitionType.SD_CARD
