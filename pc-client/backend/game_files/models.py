"""Pydantic 数据模型 for game_files 模块。"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class GameType(str, Enum):
    """游戏文件类型枚举。"""
    BASE = "base"       # 本体
    UPDATE = "update"   # 更新补丁
    DLC = "dlc"         # 追加内容


class GameFile(BaseModel):
    """单个游戏文件描述。"""
    path: str = Field(..., description="文件绝对路径")
    name: str = Field(..., description="文件名")
    game_type: GameType = Field(..., description="文件类型：base/update/dlc")
    priority: int = Field(default=0, description="安装优先级，0=本体 1=更新 2=DLC")
    size_mb: float = Field(..., description="文件大小(MB)")

    @field_validator("path")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        return str(Path(v))

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class CheatFile(BaseModel):
    """金手指压缩包描述。"""
    path: str = Field(..., description="文件绝对路径")
    name: str = Field(..., description="文件名")

    @field_validator("path")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        return str(Path(v))


class ScanResult(BaseModel):
    """扫描结果汇总。"""
    games: list[GameFile] = Field(default_factory=list)
    cheats: list[CheatFile] = Field(default_factory=list)
    total_size_mb: float = Field(default=0.0)
    base_count: int = Field(default=0)
    update_count: int = Field(default=0)
    dlc_count: int = Field(default=0)
    cheat_count: int = Field(default=0)
