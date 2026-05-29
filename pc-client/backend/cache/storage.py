"""Disk space monitoring and automatic cache cleanup."""

from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path

from .models import CacheManifest

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD_GB = 5.0


def get_free_space_gb(directory: str | Path) -> float:
    """Return free disk space in GB for the volume containing *directory*."""
    if isinstance(directory, str):
        directory = Path(directory)
    try:
        usage = shutil.disk_usage(directory)
        return usage.free / (1024 ** 3)
    except FileNotFoundError:
        volume = _find_existing_parent(directory)
        usage = shutil.disk_usage(volume)
        return usage.free / (1024 ** 3)


def get_cache_size_gb(cache_dir: str | Path) -> float:
    """Calculate total cached file size in GB (disk usage of cache directory)."""
    total = 0
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return 0.0
    for entry in cache_path.iterdir():
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            for f in entry.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
    return total / (1024 ** 3)


def check_and_clean(
    cache_dir: str | Path,
    manifest: CacheManifest,
    threshold_gb: float = DEFAULT_THRESHOLD_GB,
) -> int:
    """Check free disk space; if below threshold, evict oldest cache entries.

    Returns number of entries removed.
    """
    free = get_free_space_gb(cache_dir)
    if free >= threshold_gb:
        return 0

    logger.warning(
        "Free disk space %.1f GB < threshold %.1f GB — starting cache eviction",
        free, threshold_gb,
    )
    return _evict_oldest(cache_dir, manifest, target_free_gb=threshold_gb)


def _evict_oldest(
    cache_dir: str | Path,
    manifest: CacheManifest,
    target_free_gb: float,
) -> int:
    """Evict entries sorted by last_access (oldest first) until enough space freed.

    Called when free space dips below threshold.  Continues until either
    free space >= target_free_gb or the manifest is empty.
    """
    cache_path = Path(cache_dir)
    if not manifest.entries:
        return 0

    sorted_keys = sorted(
        manifest.entries.keys(),
        key=lambda k: manifest.entries[k].last_accessed_at,
    )

    removed = 0
    for key in sorted_keys:
        entry = manifest.entries[key]
        file = cache_path / entry.file_path
        try:
            if file.exists():
                file.unlink()
        except OSError as exc:
            logger.error("Failed to remove cached file %s: %s", file, exc)
            continue

        manifest.remove(key)
        removed += 1

        free = get_free_space_gb(cache_dir)
        if free >= target_free_gb:
            break

    return removed


def _find_existing_parent(path: Path) -> Path:
    """Walk up the directory tree until an existing path is found."""
    current = path.resolve()
    while not current.exists() and current != current.parent:
        current = current.parent
    return current
