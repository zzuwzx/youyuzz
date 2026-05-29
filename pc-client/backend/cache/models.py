"""Pydantic models for cache management module."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CacheEntry(BaseModel):
    """单条缓存记录元数据。"""

    key: str = Field(..., description="缓存唯一键（游戏名+版本哈希）")
    file_path: str = Field(..., description="缓存目录内的文件路径")
    original_name: str = Field(default="", description="原始文件名")
    game_name: str = Field(default="", description="游戏名称")
    game_version: str = Field(default="", description="游戏版本号")
    file_size: int = Field(default=0, description="文件大小（字节）")
    created_at: float = Field(default_factory=time.time, description="创建时间戳")
    ttl_days: int = Field(default=1, description="缓存有效期（天）")
    last_accessed_at: float = Field(default_factory=time.time, description="最后访问时间戳")

    @property
    def expires_at(self) -> float:
        return self.created_at + self.ttl_days * 86400

    def is_expired(self) -> bool:
        """基于文件修改时间判断 TTL 是否过期。"""
        return time.time() > self.expires_at

    @staticmethod
    def make_key(game_name: str, version: str) -> str:
        raw = f"{game_name}:{version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CacheManifest(BaseModel):
    """缓存元数据清单（持久化为 JSON）。"""

    version: int = Field(default=1, description="清单格式版本")
    updated_at: float = Field(default_factory=time.time, description="最后更新时间戳")
    entries: dict[str, CacheEntry] = Field(default_factory=dict, description="key -> CacheEntry 映射")

    def add(self, entry: CacheEntry) -> None:
        self.entries[entry.key] = entry
        self.updated_at = time.time()

    def remove(self, key: str) -> Optional[CacheEntry]:
        entry = self.entries.pop(key, None)
        if entry is not None:
            self.updated_at = time.time()
        return entry

    def get(self, key: str) -> Optional[CacheEntry]:
        return self.entries.get(key)

    def find_by_game(self, game_name: str) -> list[CacheEntry]:
        name_lower = game_name.lower()
        return [e for e in self.entries.values() if name_lower in e.game_name.lower()]

    def __len__(self) -> int:
        return len(self.entries)
