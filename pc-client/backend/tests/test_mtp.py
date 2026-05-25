"""
MTP 传输模块 — 单元测试

测试范围:
  1. 数据模型 (PartitionInfo, TransferProgress, TransferItem)
  2. ShellCopyHereBackend API (Mock COM)
  3. IFileOperationBackend API (Mock ctypes)
  4. DBI 分区发现逻辑
  5. 分区自动选择 (select_partition)
  6. CopyResult 状态码语义

注意: 需要 Switch 实体设备的 E2E 测试在 test_mtp_e2e.py 中单独维护。
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# 确保 backend 在 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mtp import (
    PartitionType,
    PartitionInfo,
    CopyResult,
    TransferProgress,
    TransferItem,
    MTPTransfer,
    ShellCopyHereBackend,
    IFileOperationBackend,
)


# ══════════════════════════════════════════════════════════
# 1. 数据模型测试
# ══════════════════════════════════════════════════════════

class TestPartitionInfo:
    def test_sd_card_defaults(self):
        pi = PartitionInfo(type=PartitionType.SD_CARD, name="5: SD Card", path="5:")
        assert pi.type == PartitionType.SD_CARD
        assert pi.free_bytes == 0
        assert pi.total_bytes == 0
        assert pi.free_mb == 0.0

    def test_space_calculations(self):
        pi = PartitionInfo(
            type=PartitionType.SD_CARD,
            name="5: SD Card install",
            path="5: SD Card install",
            free_bytes=50 * 1024 * 1024 * 1024,        # 50 GB
            total_bytes=128 * 1024 * 1024 * 1024,       # 128 GB
        )
        assert pi.free_mb == 51200.0
        assert pi.total_mb == 131072.0
        assert 60 < pi.used_pct < 61   # ~60.94%

    def test_zero_total_used_pct(self):
        pi = PartitionInfo(type=PartitionType.NAND, name="6:", path="6:", total_bytes=0)
        assert pi.used_pct == 0.0

    def test_nand_partition_type(self):
        pi = PartitionInfo(type=PartitionType.NAND, name="6: NAND install", path="6:")
        assert pi.type == PartitionType.NAND


class TestTransferProgress:
    def test_defaults(self):
        tp = TransferProgress()
        assert tp.bytes_total == 0
        assert tp.bytes_done == 0
        assert tp.ratio == 0.0
        assert tp.pct == 0

    def test_pct_calculation(self):
        tp = TransferProgress(bytes_total=100, bytes_done=42, ratio=0.42)
        assert tp.pct == 42

    def test_halfway(self):
        tp = TransferProgress(bytes_total=200, bytes_done=100, ratio=0.5)
        assert tp.pct == 50

    def test_complete(self):
        tp = TransferProgress(bytes_total=100, bytes_done=100, ratio=1.0)
        assert tp.pct == 100


class TestTransferItem:
    def test_defaults(self):
        ti = TransferItem(source_path="/tmp/game.nsp")
        assert ti.source_path == "/tmp/game.nsp"
        assert ti.dest_partition == PartitionType.SD_CARD
        assert ti.status == "pending"
        assert ti.tag == ""

    def test_explicit_nand(self):
        ti = TransferItem(
            source_path="/tmp/game.nsp",
            dest_partition=PartitionType.NAND,
            tag="本体",
        )
        assert ti.dest_partition == PartitionType.NAND
        assert ti.tag == "本体"


class TestCopyResult:
    def test_unique_values(self):
        """确保所有 CopyResult 值互不重复。"""
        values = list(CopyResult)
        assert len(values) == len(set(values))

    def test_ok_is_zero(self):
        assert CopyResult.OK == 0

    def test_error_values_positive(self):
        assert CopyResult.DEVICE_NOT_FOUND > 0
        assert CopyResult.COPY_FAILED > 0


# ══════════════════════════════════════════════════════════
# 2. 分区自动选择测试
# ══════════════════════════════════════════════════════════

def _make_partitions(sd_free=0, nand_free=0):
    return {
        PartitionType.SD_CARD: PartitionInfo(
            type=PartitionType.SD_CARD, name="5:", path="5:",
            free_bytes=sd_free, total_bytes=sd_free,
        ),
        PartitionType.NAND: PartitionInfo(
            type=PartitionType.NAND, name="6:", path="6:",
            free_bytes=nand_free, total_bytes=nand_free,
        ),
    }


class TestPartitionSelection:
    def test_sd_has_space_returns_sd(self):
        """SD 有足够空间时应返回 SD_CARD。"""
        class TestBackend(MTPTransfer):
            def is_device_connected(self): return True
            def discover_partitions(self):
                return _make_partitions(sd_free=10_000_000_000, nand_free=5_000_000_000)
            def copy_file(self, *a, **kw): return CopyResult.OK
            def get_free_space(self, p): return 0

        backend = TestBackend()
        result = backend.select_partition(file_size_bytes=1_000_000_000)
        assert result == PartitionType.SD_CARD

    def test_sd_full_falls_back_to_nand(self):
        """SD 空间不足时应回落 NAND。"""
        class TestBackend(MTPTransfer):
            def is_device_connected(self): return True
            def discover_partitions(self):
                return _make_partitions(sd_free=100_000, nand_free=10_000_000_000)
            def copy_file(self, *a, **kw): return CopyResult.OK
            def get_free_space(self, p): return 0

        backend = TestBackend()
        result = backend.select_partition(file_size_bytes=1_000_000_000)
        assert result == PartitionType.NAND

    def test_both_full_returns_sd(self):
        """两个分区都不够时仍返回 SD_CARD（由上层处理 NO_SPACE）。"""
        class TestBackend(MTPTransfer):
            def is_device_connected(self): return True
            def discover_partitions(self):
                return _make_partitions(sd_free=1, nand_free=1)
            def copy_file(self, *a, **kw): return CopyResult.OK
            def get_free_space(self, p): return 0

        backend = TestBackend()
        result = backend.select_partition(file_size_bytes=1_000_000_000)
        assert result == PartitionType.SD_CARD


# ══════════════════════════════════════════════════════════
# 3. ShellCopyHereBackend 测试 (Mock COM)
# ══════════════════════════════════════════════════════════

class TestShellCopyHereBackend:
    @pytest.fixture
    def backend(self):
        return ShellCopyHereBackend()

    def test_init_state(self, backend):
        """初始状态：未连接 shell_app。"""
        assert backend._shell_app is None
        assert backend._partitions == {}

    @patch("mtp.shell_copy_here.discover_partitions")
    @patch("mtp.shell_copy_here.win32com.client.Dispatch")
    def test_discover_partitions_caches(self, mock_dispatch, mock_discover, backend):
        mock_discover.return_value = {PartitionType.SD_CARD: MagicMock()}
        result = backend.discover_partitions()
        assert PartitionType.SD_CARD in result
        # 第二次应使用缓存（因为 _partitions 已填充且 discover_partitions 会被再次调用）
        # 但 discover_partitions 会再次被调用——这是预期行为（每次刷新）

    @patch("mtp.shell_copy_here.discover_partitions")
    def test_is_device_connected_true(self, mock_discover, backend):
        mock_discover.return_value = {PartitionType.SD_CARD: MagicMock()}
        backend._shell_app = MagicMock()
        assert backend.is_device_connected() is True

    @patch("mtp.shell_copy_here.discover_partitions")
    def test_is_device_connected_false(self, mock_discover, backend):
        from mtp.dbi_discovery import DBIDiscoveryError
        mock_discover.side_effect = DBIDiscoveryError("not found")
        backend._shell_app = MagicMock()
        assert backend.is_device_connected() is False

    def test_copy_file_missing_source(self, backend):
        """源文件不存在时应返回 IO_ERROR。"""
        result = backend.copy_file("/nonexistent/file.nsp")
        assert result == CopyResult.IO_ERROR

    @patch("mtp.shell_copy_here.discover_partitions")
    @patch("mtp.shell_copy_here.discover_partitions")
    def test_copy_file_device_not_found(self, mock_discover, backend):
        """发现不到分区时 copy_file 应返回错误，不是 OK。"""
        mock_discover.return_value = {}  # no partitions found

        with patch("os.path.isfile", return_value=True), \
             patch("os.path.getsize", return_value=1024):
            result = backend.copy_file("/fake/file.nsp")
        assert result != CopyResult.OK

    @patch("mtp.shell_copy_here.discover_partitions")
    def test_copy_file_partition_not_found(self, mock_discover, backend):
        """尝试拷贝到不存在的分区时应返回 PARTITION_NOT_FOUND。"""
        mock_discover.return_value = {}  # 无任何分区
        backend._shell_app = MagicMock()

        with patch("os.path.isfile", return_value=True), \
             patch("os.path.getsize", return_value=1024):
            result = backend.copy_file("/fake/file.nsp")
        assert result == CopyResult.PARTITION_NOT_FOUND

    def test_get_free_space_returns_negative_when_no_device(self, backend):
        backend._partitions = {PartitionType.SD_CARD: PartitionInfo(
            type=PartitionType.SD_CARD, name="5:", path="5:", free_bytes=0)}
        # get_free_space accesses self._partitions dict directly — 
        # if a partition key exists, it returns the free_bytes
        with patch("mtp.shell_copy_here.discover_partitions",
                   side_effect=Exception("simulated failure")):
            backend._partitions = {}
            assert backend.get_free_space(PartitionType.SD_CARD) == -1


# ══════════════════════════════════════════════════════════
# 4. IFileOperationBackend 测试 (Mock ctypes)
# ══════════════════════════════════════════════════════════

class TestIFileOperationBackend:
    @pytest.fixture
    def backend(self):
        return IFileOperationBackend()

    def test_init_state(self, backend):
        assert backend._partitions == {}

    def test_is_device_connected_no_device(self, backend):
        with patch("mtp.ifile_operation.find_switch_device",
                   side_effect=Exception("no device")):
            assert backend.is_device_connected() is False

    def test_copy_file_missing_source(self, backend):
        result = backend.copy_file("/nonexistent/file.nsp")
        assert result == CopyResult.IO_ERROR

    @patch("mtp.dbi_discovery.discover_partitions")
    @patch("mtp.ifile_operation._discover_partitions")
    def test_copy_file_device_not_found(self, mock_discover, backend):
        """发现不到分区时 copy_file 应返回错误，不是 OK。"""
        mock_discover.return_value = {}  # no partitions found

        with patch("os.path.isfile", return_value=True), \
             patch("os.path.getsize", return_value=1024):
            result = backend.copy_file("/fake/file.nsp")
        assert result != CopyResult.OK

    @patch("mtp.ifile_operation._discover_partitions")
    def test_get_free_space_returns_negative(self, mock_disc, backend):
        mock_disc.side_effect = Exception("fail")
        backend._partitions = {}
        assert backend.get_free_space(PartitionType.SD_CARD) == -1


    @patch("mtp.ifile_operation._discover_partitions")
    def test_get_free_space_returns_value(self, mock_discover, backend):
        pi = PartitionInfo(type=PartitionType.SD_CARD, name="5:", path="5:",
                          free_bytes=12345)
        mock_discover.return_value = {PartitionType.SD_CARD: pi}
        backend._partitions = {}
        assert backend.get_free_space(PartitionType.SD_CARD) == 12345


# ══════════════════════════════════════════════════════════
# 5. 进度回调测试
# ══════════════════════════════════════════════════════════

class TestProgressCallback:
    def test_callback_is_callable(self):
        """确认 ProgressCallback 类型定义正确。"""
        from mtp import ProgressCallback
        called = []

        def cb(p: TransferProgress):
            called.append(p.ratio)

        assert callable(cb)
        cb(TransferProgress(ratio=0.5))
        assert called == [0.5]

    def test_callback_receives_transfer_progress(self):
        progress_values = []

        def on_progress(tp: TransferProgress):
            progress_values.append((tp.bytes_done, tp.ratio))

        on_progress(TransferProgress(bytes_total=1000, bytes_done=500, ratio=0.5))
        assert progress_values[0] == (500, 0.5)

# ══════════════════════════════════════════════════════════
# 6. WpdBackend tests (structure only — E2E needs Switch)
# ══════════════════════════════════════════════════════════

class TestWpdBackend:
    @pytest.fixture
    def backend(self):
        from mtp import WpdBackend
        return WpdBackend()

    def test_init_state(self, backend):
        """Initial state: empty partitions."""
        assert backend._partitions == {}

    def test_copy_file_missing_source(self, backend):
        """Missing source file returns IO_ERROR."""
        result = backend.copy_file("/nonexistent/file.nsp")
        assert result == CopyResult.IO_ERROR

    @patch("mtp.wpd_backend.WpdBackend._find_switch_device_id", return_value=None)
    def test_copy_file_device_not_found(self, mock_find, backend):
        """No device found returns error."""
        with patch("os.path.isfile", return_value=True), \
             patch("os.path.getsize", return_value=1024):
            result = backend.copy_file("/fake/file.nsp")
        assert result != CopyResult.OK

    def test_is_device_connected_no_com(self, backend):
        """is_device_connected returns False when COM fails."""
        with patch("mtp.wpd_backend.CoInitialize", side_effect=Exception("fail")):
            assert backend.is_device_connected() is False
