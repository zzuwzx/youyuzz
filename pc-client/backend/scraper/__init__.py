"""scraper: nsthwj.cn 游戏检索模块。

通过 Playwright 无头浏览器访问网站，
从 Vue 组件树直接提取游戏数据（无需 DOM 解析）。
"""

from .client import GameScraper
from .parser import parse_game_url
from .game_dict import GameNameDict
from .models import GameSearchResult, CloudDiskLink, DiskType

__all__ = [
    "GameScraper", "GameNameDict",
    "parse_game_url",
    "GameSearchResult", "CloudDiskLink", "DiskType",
]
