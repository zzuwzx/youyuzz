# 鱿郁仔仔 — API Pydantic 模型
# pc-client/backend/api/models.py

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ============================================================
#  通用
# ============================================================

class ErrorResponse(BaseModel):
    """统一错误响应体。"""
    error: str
    detail: Optional[str] = None
    code: int = 500


# ============================================================
#  搜索
# ============================================================

class SearchResultItem(BaseModel):
    """单条搜索结果。"""
    title: str
    version: Optional[str] = None
    size: Optional[str] = None
    source_url: str = ""


class SearchResponse(BaseModel):
    """搜索响应。"""
    keyword: str
    results: list[SearchResultItem] = Field(default_factory=list)
    total: int = 0


class GameDetailResponse(BaseModel):
    """游戏详情响应。"""
    title: str
    body_url: Optional[str] = None
    update_url: Optional[str] = None
    dlc_url: Optional[str] = None
    cheat_url: Optional[str] = None
    image_url: Optional[str] = None
    links: list[dict] = Field(default_factory=list)


# ============================================================
#  安装
# ============================================================

class InstallOrder(str, Enum):
    """安装顺序枚举。"""
    SEQUENTIAL = "sequential"   # 串行安装
    CONCURRENT = "concurrent"   # 并发安装（VIP）


class InstallRequest(BaseModel):
    """发起远程安装请求。"""
    game_url: str = Field(..., min_length=1, description="游戏详情页 URL")
    install_order: InstallOrder = InstallOrder.SEQUENTIAL


class LocalInstallRequest(BaseModel):
    """本地离线安装请求。"""
    folder_path: str = Field(..., min_length=1, description="本地游戏文件夹路径")


class BatchInstallRequest(BaseModel):
    """批量安装请求（VIP）。"""
    game_list: list[InstallRequest] = Field(..., min_length=1)


class InstallStage(str, Enum):
    """安装阶段枚举。"""
    QUEUED = "queued"
    SCRAPING = "scraping"
    TRANSFERRING = "transferring"   # 兼容前端旧字段名
    SAVING_TO_DISK = "saving_to_disk"
    DOWNLOADING = "downloading"
    CLASSIFYING = "classifying"
    TRANSFERRING_MTP = "transferring_mtp"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstallProgressResponse(BaseModel):
    """安装进度响应。"""
    task_id: str
    stage: InstallStage = InstallStage.QUEUED
    percent: float = 0.0
    current_file: Optional[str] = None
    speed: Optional[str] = None
    total_files: int = 0
    completed_files: int = 0
    error: Optional[str] = None


class InstallTaskResponse(BaseModel):
    """安装任务创建响应。"""
    task_id: str
    status: str = "accepted"
    message: Optional[str] = None


# ============================================================
#  设备
# ============================================================

class SwitchDeviceResponse(BaseModel):
    """Switch 设备状态。"""
    connected: bool = False
    mode: str = "DBI"
    free_space_tf: int = 0   # MB
    free_space_nand: int = 0  # MB


class TFCardResponse(BaseModel):
    """TF 卡状态。"""
    inserted: bool = False
    drive_letter: Optional[str] = None
    free_space: int = 0  # MB


# ============================================================
#  设置
# ============================================================

class SettingsResponse(BaseModel):
    """当前配置（公开字段）。"""
    host: str = "127.0.0.1"
    port: int = 18888
    version: str = "1.0.0"
    scraper_headless: bool = True
    mtp_backend: str = "shell"
    auth_server_url: str = ""
    log_level: str = "INFO"


class SettingsUpdateRequest(BaseModel):
    """配置更新请求。"""
    key: str = Field(..., min_length=1)
    value: str = ""   # 值统一为字符串，由服务端解析


class ActivateRequest(BaseModel):
    """激活码验证请求。"""
    code: str = Field(..., min_length=1, pattern=r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")


class ActivateResponse(BaseModel):
    """激活响应。"""
    success: bool
    message: str = ""
    license_key: Optional[str] = None


# ============================================================
#  系统
# ============================================================

class VersionResponse(BaseModel):
    """版本信息。"""
    current: str
    latest: Optional[str] = None
    update_url: Optional[str] = None
    changelog: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应。"""
    status: str = "ok"
    python_version: str = ""
    uptime: float = 0.0
    version: str = "1.0.0"
