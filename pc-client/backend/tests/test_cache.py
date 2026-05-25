"""Unit tests for cache management module (M5)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cache import CacheManager, CacheEntry, CacheManifest
from cache.storage import get_free_space_gb, get_cache_size_gb, check_and_clean


# ── fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def temp_cache_root() -> Path:
    p = Path(tempfile.mkdtemp(prefix="cache_test_"))
    yield p
    shutil.rmtree(p, ignore_errors=True)


@pytest.fixture
def manager(temp_cache_root: Path) -> CacheManager:
    return CacheManager(cache_dir=temp_cache_root)


@pytest.fixture
def dummy_file(temp_cache_root: Path) -> Path:
    f = temp_cache_root / "test_game.nsp"
    f.write_bytes(b"A" * 1024)
    return f


# ── models ────────────────────────────────────────────────────────

class TestCacheEntry:
    def test_make_key_deterministic(self):
        k1 = CacheEntry.make_key("塞尔达", "1.6.0")
        k2 = CacheEntry.make_key("塞尔达", "1.6.0")
        assert k1 == k2

    def test_make_key_different(self):
        k1 = CacheEntry.make_key("塞尔达", "1.6.0")
        k2 = CacheEntry.make_key("塞尔达", "1.5.0")
        assert k1 != k2

    def test_is_expired_fresh(self):
        e = CacheEntry(key="k", file_path="f", ttl_days=1)
        assert e.is_expired() is False

    def test_is_expired_old(self):
        e = CacheEntry(key="k", file_path="f", ttl_days=1,
                       created_at=time.time() - 86401)
        assert e.is_expired() is True

    def test_expires_at(self):
        e = CacheEntry(key="k", file_path="f", ttl_days=2,
                       created_at=1000.0)
        assert e.expires_at == pytest.approx(1000.0 + 172800)

    def test_model_dump_json_serializable(self):
        e = CacheEntry(key="abc", file_path="abc.nsp")
        d = e.model_dump()
        json.dumps(d)


class TestCacheManifest:
    def test_add_and_get(self):
        m = CacheManifest()
        e = CacheEntry(key="k1", file_path="f1")
        m.add(e)
        assert m.get("k1") is e
        assert len(m) == 1

    def test_remove_returns_entry(self):
        m = CacheManifest()
        e = CacheEntry(key="k1", file_path="f1")
        m.add(e)
        removed = m.remove("k1")
        assert removed is e
        assert len(m) == 0

    def test_remove_missing(self):
        m = CacheManifest()
        assert m.remove("nope") is None

    def test_find_by_game(self):
        m = CacheManifest()
        e1 = CacheEntry(key="k1", file_path="f1", game_name="塞尔达传说")
        e2 = CacheEntry(key="k2", file_path="f2", game_name="马里奥赛车")
        m.add(e1)
        m.add(e2)
        results = m.find_by_game("塞尔达")
        assert len(results) == 1
        assert results[0] is e1

    def test_find_by_game_case_insensitive(self):
        m = CacheManifest()
        e = CacheEntry(key="k1", file_path="f1", game_name="Zelda")
        m.add(e)
        assert len(m.find_by_game("zelda")) == 1

    def test_updated_at_changes(self):
        m = CacheManifest()
        t0 = m.updated_at
        time.sleep(0.01)
        e = CacheEntry(key="k1", file_path="f1")
        m.add(e)
        assert m.updated_at > t0


# ── manager: put / get ───────────────────────────────────────────

class TestPutGet:
    def test_put_and_get(self, manager, dummy_file):
        key = CacheEntry.make_key("塞尔达", "1.6.0")
        manager.put(dummy_file, key,
                    game_name="塞尔达传说", game_version="1.6.0",
                    move=False)
        result = manager.get(key)
        assert result is not None
        assert result.exists()
        assert result.stat().st_size == 1024

    def test_get_missing_key(self, manager):
        assert manager.get("nonexistent") is None

    def test_get_expired_entry(self, manager, dummy_file):
        key = CacheEntry.make_key("old", "1.0")
        manager.put(dummy_file, key, move=False, ttl_days=0)
        entry = manager.manifest.get(key)
        entry.created_at = time.time() - 10
        manager._save_manifest()
        assert manager.get(key) is None

    def test_get_file_gone(self, manager, dummy_file):
        key = CacheEntry.make_key("gone", "1.0")
        manager.put(dummy_file, key, move=False)
        entry = manager.manifest.get(key)
        (manager.root / entry.file_path).unlink()
        assert manager.get(key) is None

    def test_put_move_removes_source(self, manager):
        src = manager.root / "source.bin"
        src.write_bytes(b"X" * 512)
        key = CacheEntry.make_key("move_test", "1.0")
        manager.put(src, key, move=True)
        assert not src.exists()
        result = manager.get(key)
        assert result is not None

    def test_last_accessed_updates_on_get(self, manager, dummy_file):
        key = CacheEntry.make_key("touch", "1.0")
        manager.put(dummy_file, key, move=False)
        t0 = manager.manifest.get(key).last_accessed_at
        time.sleep(0.01)
        manager.get(key)
        t1 = manager.manifest.get(key).last_accessed_at
        assert t1 > t0

    def test_find_by_game(self, manager, dummy_file):
        key1 = CacheEntry.make_key("zelda", "1.0")
        key2 = CacheEntry.make_key("mario", "1.0")
        manager.put(dummy_file, key1, game_name="塞尔达传说", move=False)
        manager.put(dummy_file, key2, game_name="马里奥赛车8", move=False)
        hits = manager.find_by_game("塞尔达")
        assert len(hits) == 1
        assert hits[0].game_name == "塞尔达传说"


# ── manager: evict / clear ───────────────────────────────────────

class TestEviction:
    def test_invalidate_existing(self, manager, dummy_file):
        key = CacheEntry.make_key("z", "1")
        manager.put(dummy_file, key, move=False)
        assert manager.invalidate(key) is True
        assert manager.get(key) is None

    def test_invalidate_missing(self, manager):
        assert manager.invalidate("nope") is False

    def test_purge_expired(self, manager, dummy_file):
        fresh_key = CacheEntry.make_key("fresh", "1")
        stale_key = CacheEntry.make_key("stale", "1")
        manager.put(dummy_file, fresh_key, move=False, ttl_days=10)
        manager.put(dummy_file, stale_key, move=False, ttl_days=0)
        entry = manager.manifest.get(stale_key)
        entry.created_at = time.time() - 100
        manager._save_manifest()
        removed = manager.purge_expired()
        assert removed == 1
        assert manager.get(fresh_key) is not None
        assert manager.get(stale_key) is None

    def test_clear(self, manager, dummy_file):
        manager.put(dummy_file, CacheEntry.make_key("a", "1"), move=False)
        manager.put(dummy_file, CacheEntry.make_key("b", "1"), move=False)
        assert manager.entry_count == 2
        removed = manager.clear()
        assert removed == 2
        assert manager.entry_count == 0


# ── persistence ───────────────────────────────────────────────────

class TestPersistence:
    def test_manifest_roundtrip(self, manager, dummy_file):
        key = CacheEntry.make_key("rtt", "1.0")
        manager.put(dummy_file, key, game_name="RTT Game", move=False)
        m2 = CacheManager(cache_dir=manager.root)
        entry = m2.get(key)
        assert entry is not None
        assert entry.exists()
        assert m2.manifest.get(key).game_name == "RTT Game"

    def test_corrupt_manifest_fallback(self, manager):
        (manager.root / "metadata.json").write_text("not valid json///")
        m2 = CacheManager(cache_dir=manager.root)
        assert m2.entry_count == 0


# ── storage ───────────────────────────────────────────────────────

class TestStorage:
    def test_get_free_space_gb(self, temp_cache_root):
        free = get_free_space_gb(temp_cache_root)
        assert free > 0

    def test_get_cache_size_gb_empty(self, temp_cache_root):
        assert get_cache_size_gb(temp_cache_root) == pytest.approx(0.0)

    def test_get_cache_size_gb_with_files(self, manager):
        (manager.root / "dummy.bin").write_bytes(b"B" * 2_000_000)
        size = get_cache_size_gb(manager.root)
        assert size > 0

    def test_check_and_clean_noop_when_plenty(self, manager):
        m = CacheManifest()
        removed = check_and_clean(manager.root, m, threshold_gb=0.0)
        assert removed == 0

    def test_check_and_clean_evicts(self, manager):
        (manager.root / "f1").write_bytes(b"0")
        (manager.root / "f2").write_bytes(b"0")
        e1 = CacheEntry(key="k1", file_path="f1",
                        last_accessed_at=100.0)
        e2 = CacheEntry(key="k2", file_path="f2",
                        last_accessed_at=200.0)
        manifest = CacheManifest()
        manifest.add(e1)
        manifest.add(e2)
        removed = check_and_clean(manager.root, manifest, threshold_gb=9999)
        assert removed == 2
        assert len(manifest) == 0

    def test_evict_stops_when_free(self, manager):
        """With an impossibly high threshold, all entries get evicted."""
        (manager.root / "f1").write_bytes(b"0")
        e1 = CacheEntry(key="k1", file_path="f1",
                        last_accessed_at=100.0)
        manifest = CacheManifest()
        manifest.add(e1)
        removed = check_and_clean(manager.root, manifest,
                                  threshold_gb=999999)
        assert removed == 1


# ── edge cases ────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_cache(self, manager):
        assert manager.entry_count == 0
        assert manager.size_gb == pytest.approx(0.0)
        assert manager.get("anything") is None

    def test_put_non_existent_source(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.put(manager.root / "ghost.bin", "key")

    def test_same_key_overwrites(self, manager, dummy_file):
        key = CacheEntry.make_key("dup", "1")
        manager.put(dummy_file, key, move=False)
        manager.put(dummy_file, key, move=False, game_name="v2")
        assert manager.manifest.get(key).game_name == "v2"


# ── M5 checklist coverage ────────────────────────────────────────

class TestChecklistCoverage:
    """Each test maps to a checklist item in docs/modules/M5_缓存管理.md."""

    def test_cache_write(self, manager, dummy_file):
        key = CacheEntry.make_key("write_test", "1.0")
        entry = manager.put(dummy_file, key, game_name="缓存写入测试", move=True)
        assert not Path(dummy_file).exists()
        meta = manager.manifest.get(key)
        assert meta is not None
        assert meta.game_name == "缓存写入测试"

    def test_cache_hit_check(self, manager, dummy_file):
        key = CacheEntry.make_key("hit_test", "1.0")
        manager.put(dummy_file, key, game_name="命中测试", move=False)
        result = manager.get(key)
        assert result is not None

    def test_ttl_expired(self, manager, dummy_file):
        key = CacheEntry.make_key("ttl_test", "1.0")
        manager.put(dummy_file, key, move=False, ttl_days=0)
        entry = manager.manifest.get(key)
        entry.created_at = time.time() - 86401
        manager._save_manifest()
        assert manager.get(key) is None

    def test_space_monitoring(self, manager):
        manifest = CacheManifest()
        check_and_clean(manager.root, manifest, threshold_gb=1.0)

    def test_metadata_persistence(self, manager, dummy_file):
        key = CacheEntry.make_key("json_test", "1.0")
        manager.put(dummy_file, key, game_name="JSON持久化测试", move=False)
        raw = json.loads(
            (manager.root / "metadata.json").read_text(encoding="utf-8")
        )
        assert "entries" in raw
        assert key in raw["entries"]

    def test_auto_sweep_on_get(self, manager, dummy_file):
        fresh = CacheEntry.make_key("fresh", "1")
        stale = CacheEntry.make_key("stale", "1")
        manager.put(dummy_file, fresh, move=False, ttl_days=30)
        manager.put(dummy_file, stale, move=False, ttl_days=0)
        e = manager.manifest.get(stale)
        e.created_at = time.time() - 100
        manager._save_manifest()
        _ = manager.get(fresh)
        assert manager.manifest.get(stale) is None

    def test_manifest_atomic_write(self, manager, dummy_file):
        key = CacheEntry.make_key("atomic", "1")
        manager.put(dummy_file, key, move=False)
        tmp = manager.root / "metadata.json.tmp"
        assert not tmp.exists()
