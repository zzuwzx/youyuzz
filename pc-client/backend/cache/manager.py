"""Cache manager: read/write/evict with TTL and JSON-backed metadata."""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from .models import CacheEntry, CacheManifest
from .storage import check_and_clean

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "metadata.json"


def _cache_root() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "youyuzz" / "cache"


class CacheManager:
    """Local file cache with TTL expiration and disk-space-aware eviction.

    Files are stored under `%APPDATA%/youyuzz/cache/`.  Metadata is kept
    in `metadata.json` at the same location.
    """

    def __init__(self, cache_dir: Optional[str | Path] = None) -> None:
        self.root = Path(cache_dir) if cache_dir else _cache_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.root / MANIFEST_FILENAME
        self.manifest = self._load_manifest()

    # ── public API ────────────────────────────────────────────────

    def put(
        self,
        src_path: str | Path,
        key: str,
        *,
        game_name: str = "",
        game_version: str = "",
        original_name: str = "",
        ttl_days: int = 1,
        move: bool = True,
    ) -> CacheEntry:
        """Write a file into the cache and record its metadata."""
        self._sweep_expired()

        src = Path(src_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        dest_name = key + (src.suffix or "")
        dest = self.root / dest_name

        if move:
            shutil.move(str(src), str(dest))
        else:
            shutil.copy2(str(src), str(dest))

        file_size = dest.stat().st_size
        now = time.time()

        entry = CacheEntry(
            key=key,
            file_path=dest_name,
            original_name=original_name or src.name,
            game_name=game_name,
            game_version=game_version,
            file_size=file_size,
            created_at=now,
            ttl_days=ttl_days,
            last_accessed_at=now,
        )

        self.manifest.add(entry)
        self._save_manifest()

        # 写入后检查磁盘空间
        removed = check_and_clean(self.root, self.manifest)
        if removed:
            self._save_manifest()
            logger.info("Evicted %d stale entries after put", removed)

        return entry

    def get(self, key: str) -> Optional[Path]:
        """Look up a cache entry by key.  Returns the file path if valid, or
        `None` when missing or expired."""
        self._sweep_expired()

        entry = self.manifest.get(key)
        if entry is None:
            return None

        if entry.is_expired():
            self._remove_file_and_entry(entry)
            self._save_manifest()
            return None

        file = self.root / entry.file_path
        if not file.exists():
            self.manifest.remove(key)
            self._save_manifest()
            return None

        # 更新最后访问时间
        entry.last_accessed_at = time.time()
        self._save_manifest()
        return file

    def find_by_game(self, game_name: str) -> list[CacheEntry]:
        """Return all cache entries matching a game name (case-insensitive
        substring)."""
        self._sweep_expired()
        return self.manifest.find_by_game(game_name)

    def invalidate(self, key: str) -> bool:
        """Remove a specific entry and its file.  Returns True if it existed."""
        entry = self.manifest.get(key)
        if entry is None:
            return False
        self._remove_file_and_entry(entry)
        self._save_manifest()
        return True

    def purge_expired(self) -> int:
        """Remove all TTL-expired entries.  Returns count removed."""
        count = self._sweep_expired()
        if count:
            self._save_manifest()
        return count

    def clear(self) -> int:
        """Remove every cached file and reset the manifest.  Returns count."""
        total = len(self.manifest)
        for entry in list(self.manifest.entries.values()):
            file = self.root / entry.file_path
            try:
                if file.exists():
                    file.unlink()
            except OSError:
                pass
        self.manifest.entries.clear()
        self._save_manifest()
        return total

    @property
    def entry_count(self) -> int:
        return len(self.manifest)

    @property
    def size_gb(self) -> float:
        from .storage import get_cache_size_gb
        return get_cache_size_gb(self.root)

    # ── persistence ───────────────────────────────────────────────

    def _load_manifest(self) -> CacheManifest:
        """Load metadata from disk, falling back to an empty manifest."""
        if not self._manifest_path.exists():
            return CacheManifest()

        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to read cache manifest; starting fresh")
            return CacheManifest()

        entries = {}
        for key, raw in data.get("entries", {}).items():
            try:
                entries[key] = CacheEntry.model_validate(raw)
            except Exception:
                logger.warning("Skipping corrupt cache entry key=%s", key)

        return CacheManifest(
            version=data.get("version", 1),
            updated_at=data.get("updated_at", time.time()),
            entries=entries,
        )

    def _save_manifest(self) -> None:
        """Persist the manifest atomically."""
        self.manifest.updated_at = time.time()
        data = {
            "version": self.manifest.version,
            "updated_at": self.manifest.updated_at,
            "entries": {
                key: entry.model_dump() for key, entry in self.manifest.entries.items()
            },
        }
        tmp = self._manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._manifest_path)

    # ── helpers ───────────────────────────────────────────────────

    def _sweep_expired(self) -> int:
        """Remove entries whose TTL has lapsed.  Returns count removed."""
        expired = [
            key for key, e in self.manifest.entries.items() if e.is_expired()
        ]
        for key in expired:
            entry = self.manifest.entries[key]
            self._remove_file_and_entry(entry)
        return len(expired)

    def _remove_file_and_entry(self, entry: CacheEntry) -> None:
        """Safely remove cached file and its manifest entry."""
        file = self.root / entry.file_path
        try:
            if file.exists():
                file.unlink()
        except OSError as exc:
            logger.error("Failed to remove cached file %s: %s", file, exc)
        self.manifest.remove(entry.key)
