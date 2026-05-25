# -*- coding: utf-8 -*-

"""MTP E2E integration tests - requires Switch device + DBI running."""

import os, sys, tempfile, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mtp import PartitionType, CopyResult, TransferProgress, ShellCopyHereBackend

def _device_connected():
    try:
        b = ShellCopyHereBackend()
        return b.is_device_connected()
    except Exception:
        return False

def _create_temp_file(size_bytes, suffix='.bin'):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'wb') as f:
        f.write(os.urandom(size_bytes))
    return path

@pytest.mark.skipif(not _device_connected(), reason='Switch not connected -- skipping E2E')
class TestMtpE2E:
    @pytest.fixture(autouse=True)
    def backend(self):
        b = ShellCopyHereBackend()
        b.discover_partitions()
        return b

    def test_discover_partitions(self, backend):
        parts = backend._partitions
        assert PartitionType.SD_CARD in parts
        assert PartitionType.NAND in parts
        assert parts[PartitionType.SD_CARD].total_bytes > 0

    def test_copy_small_file(self, backend):
        tmp = _create_temp_file(1024)
        try:
            result = backend.copy_file(tmp, PartitionType.SD_CARD)
            assert result == CopyResult.OK
        finally:
            os.unlink(tmp)

    def test_progress_callback(self, backend):
        tmp = _create_temp_file(10 * 1024 * 1024)
        snapshots = []

        def cb(p):
            snapshots.append(p.ratio)

        try:
            result = backend.copy_file(tmp, PartitionType.SD_CARD, on_progress=cb)
            assert result == CopyResult.OK
        finally:
            os.unlink(tmp)

        assert len(snapshots) >= 3
        assert snapshots[-1] == 1.0
