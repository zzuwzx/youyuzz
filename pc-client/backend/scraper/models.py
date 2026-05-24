"""Pydantic models for scraper module."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DiskType(str, Enum):
    QUARK = "quark"
    BAIDU = "baidu"
    ALIYUN = "aliyun"
    UNKNOWN = "unknown"


class CloudDiskLink(BaseModel):
    """单个网盘链接。"""
    disk_type: DiskType
    url: str
    password: Optional[str] = None


class GameSearchResult(BaseModel):
    """搜索命中结果。"""
    name: str = Field(..., description="完整游戏名称（中文|英文）")
    name_cn: str = Field(default="", description="中文名")
    name_en: str = Field(default="", description="英文名")
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    links: list[CloudDiskLink] = Field(default_factory=list)
    version: Optional[str] = Field(default=None, description="版本号")
    has_cheats: bool = Field(default=False, description="是否含金手指")
    raw_url: str = Field(default="", description="原始url字段")
    similarity: float = Field(default=1.0, description="搜索匹配相似度(0-1)")
