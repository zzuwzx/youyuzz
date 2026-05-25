# 鱿郁仔仔 — 全局配置
# pc-client/backend/config.py

from __future__ import annotations

import os
import platform
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Config:
    """全局应用配置，单例模式。"""

    # -- 服务 --
    HOST: str = "127.0.0.1"
    PORT: int = 18888
    APP_NAME: str = "鱿郁仔仔"
    VERSION: str = "1.0.0"

    # -- 路径 --
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    CACHE_DIR: Path = field(default_factory=lambda: _default_cache_dir())
    DATA_DIR: Path = field(default_factory=lambda: _default_data_dir())
    LOG_DIR: Path = field(default_factory=lambda: _default_log_dir())

    # -- 网盘 --
    DISK_COOKIE_DIR: Path = field(default_factory=lambda: _default_data_dir() / "cookies")

    # -- 爬虫 --
    SCRAPER_HEADLESS: bool = True
    SCRAPER_TIMEOUT_MS: int = 15000

    # -- MTP --
    MTP_PREFERRED_BACKEND: str = "shell"  # "wpd" | "shell" | "ifileoperation"

    # -- 授权 --
    AUTH_SERVER_URL: str = ""  # Cloudflare Workers URL，Phase 2 填写

    # -- 日志 --
    LOG_LEVEL: str = "INFO"


def _default_cache_dir() -> Path:
    """缓存目录: %APPDATA%/youyuzz/cache"""
    appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(appdata) / "youyuzz" / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _default_data_dir() -> Path:
    """数据目录: %APPDATA%/youyuzz/data"""
    appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(appdata) / "youyuzz" / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _default_log_dir() -> Path:
    """日志目录: %APPDATA%/youyuzz/logs"""
    appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(appdata) / "youyuzz" / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


# 全局单例
config = Config()
