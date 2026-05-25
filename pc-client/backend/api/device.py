# 鱿郁仔仔 — 设备检测路由
# pc-client/backend/api/device.py

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from .models import SwitchDeviceResponse, TFCardResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 由 main.py 注入
_mtp_backend = None


def set_mtp_backend(backend) -> None:
    global _mtp_backend
    _mtp_backend = backend


# ============================================================
#  GET /api/device/switch
# ============================================================

@router.get("/device/switch", response_model=SwitchDeviceResponse)
async def switch_device_status():
    """检测 Switch DBI MTP 连接状态。"""
    if _mtp_backend is None:
        # 未初始化后端时返回默认值（不报错，前端可正常处理）
        return SwitchDeviceResponse()

    try:
        connected = _mtp_backend.is_device_connected()
        if not connected:
            return SwitchDeviceResponse(connected=False)

        partitions = _mtp_backend.discover_partitions()

        # MTP base 模块的 PartitionType: SD_CARD=5, NAND=6
        from mtp.base import PartitionType
        sd = partitions.get(PartitionType.SD_CARD)
        nand = partitions.get(PartitionType.NAND)

        return SwitchDeviceResponse(
            connected=True,
            mode="DBI",
            free_space_tf=int(sd.free_mb) if sd else 0,
            free_space_nand=int(nand.free_mb) if nand else 0,
        )
    except Exception as exc:
        logger.exception("获取 Switch 设备状态失败")
        raise HTTPException(status_code=500, detail=f"设备检测异常: {exc}")


# ============================================================
#  GET /api/device/tfcard
# ============================================================

@router.get("/device/tfcard", response_model=TFCardResponse)
async def tfcard_status():
    """检测 TF 卡读卡器状态（Windows 盘符）。"""
    import ctypes
    import string

    try:
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                drives.append(f"{letter}:\\")
    except Exception:
        # 非 Windows 环境或无权限时回退
        return TFCardResponse()

    # 优先查找可移动驱动器
    removable_drives = []
    fixed_drives = []
    for d in drives:
        try:
            dtype = ctypes.windll.kernel32.GetDriveTypeW(d)
            if dtype == 2:   # DRIVE_REMOVABLE
                removable_drives.append(d)
            elif dtype == 3:  # DRIVE_FIXED
                fixed_drives.append(d)
        except Exception:
            fixed_drives.append(d)

    candidates = removable_drives + fixed_drives

    for drive in candidates:
        try:
            import shutil
            usage = shutil.disk_usage(drive)
            free_mb = usage.free // (1024 * 1024)
            if free_mb > 0:
                return TFCardResponse(
                    inserted=True,
                    drive_letter=drive.rstrip("\\"),
                    free_space=free_mb,
                )
        except OSError:
            continue

    return TFCardResponse()
