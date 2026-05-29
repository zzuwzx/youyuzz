"""cache: 本地文件缓存管理模块。

提供缓存写入、命中检测、TTL 过期管理、磁盘空间监控
与自动清理等功能。缓存目录位于 `%APPDATA%/youyuzz/cache/`，
元数据以 JSON 格式持久化。
"""

from .manager import CacheManager
from .models import CacheEntry, CacheManifest
from .storage import get_free_space_gb, get_cache_size_gb, check_and_clean

__all__ = [
    "CacheManager",
    "CacheEntry",
    "CacheManifest",
    "get_free_space_gb",
    "get_cache_size_gb",
    "check_and_clean",
]
