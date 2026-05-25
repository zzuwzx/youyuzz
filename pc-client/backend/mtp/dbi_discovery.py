"""
DBI 分区发现模块

通过 Windows Shell.Application Namespace 枚举 MTP 设备，
识别 Switch DBI 分区: 第5分区=TF卡(SD Card), 第6分区=NAND(机身内存)。

参考: SquidInstallerGUI.py bg_install_worker 中的设备发现逻辑。
"""
import logging
from typing import Optional

import win32com.client
import pythoncom

from .base import PartitionType, PartitionInfo

logger = logging.getLogger(__name__)

# Shell NameSpace 常量
SSF_DRIVES = 17       # 我的电脑 / 此电脑

# DBI MTP 分区名称模式
SD_INSTALL_MARKERS = ["5:", "SD Card", "MicroSD", "sd card"]
NAND_INSTALL_MARKERS = ["6:", "NAND", "nand", "Internal"]
CHEAT_MARKERS = ["金手指", "cheat", "cht"]
SWITCH_DEVICE_MARKER = "Switch"


class DBIDiscoveryError(Exception):
    """DBI 设备发现异常"""
    pass


def find_switch_device():
    """
    查找 Switch MTP 设备。

    Returns:
        (switch_item, shell_app) 元组。
        switch_item 为 Switch 设备的 Shell FolderItem。

    Raises:
        DBIDiscoveryError: 未找到 Switch 设备时抛出。
    """
    pythoncom.CoInitialize()
    try:
        shell_app = win32com.client.Dispatch("Shell.Application")
        my_computer = shell_app.NameSpace(SSF_DRIVES)

        for item in my_computer.Items():
            if SWITCH_DEVICE_MARKER in item.Name:
                return item, shell_app

        raise DBIDiscoveryError("未检测到 Switch MTP 设备——请确认 DBI 已启动并连接 USB")
    finally:
        pythoncom.CoUninitialize()


def discover_partitions(shell_app=None) -> dict[PartitionType, PartitionInfo]:
    """
    扫描 DBI MTP 全部分区。

    Args:
        shell_app: 可选，已 Dispatch 的 Shell.Application 对象。
                   传 None 时内部创建。

    Returns:
        {PartitionType: PartitionInfo} 映射表。
        至少包含 SD_CARD 和 NAND 两个分区。
    """
    pythoncom.CoInitialize()
    try:
        if shell_app is None:
            shell_app = win32com.client.Dispatch("Shell.Application")

        my_computer = shell_app.NameSpace(SSF_DRIVES)
        switch_item = None

        for item in my_computer.Items():
            if SWITCH_DEVICE_MARKER in item.Name:
                switch_item = item
                break

        if switch_item is None:
            raise DBIDiscoveryError("未检测到 Switch MTP 设备")

        partitions: dict[PartitionType, PartitionInfo] = {}
        switch_folder = switch_item.GetFolder

        for sub in switch_folder.Items():
            name = sub.Name
            name_lower = name.lower()

            if any(m.lower() in name_lower for m in SD_INSTALL_MARKERS):
                ptype = PartitionType.SD_CARD
                free, total = _query_space(sub)
                partitions[ptype] = PartitionInfo(
                    type=ptype,
                    name=name,
                    path=name,
                    free_bytes=free,
                    total_bytes=total,
                )
                logger.info("发现 TF 卡分区: %s (可用 %d MB / 总计 %d MB)",
                            name, free // (1024 * 1024), total // (1024 * 1024))

            elif any(m.lower() in name_lower for m in NAND_INSTALL_MARKERS):
                ptype = PartitionType.NAND
                free, total = _query_space(sub)
                partitions[ptype] = PartitionInfo(
                    type=ptype,
                    name=name,
                    path=name,
                    free_bytes=free,
                    total_bytes=total,
                )
                logger.info("发现 NAND 分区: %s (可用 %d MB / 总计 %d MB)",
                            name, free // (1024 * 1024), total // (1024 * 1024))

            elif any(m in name_lower for m in CHEAT_MARKERS):
                # 记录金手指目录，但不作为安装分区
                logger.info("发现金手指目录: %s", name)

        if PartitionType.SD_CARD not in partitions and PartitionType.NAND not in partitions:
            raise DBIDiscoveryError(
                "已找到 Switch 设备，但未识别到 DBI 安装分区 "
                "(期望 5: SD Card install 或 6: NAND install)"
            )

        return partitions
    finally:
        pythoncom.CoUninitialize()


def _query_space(folder_item) -> tuple[int, int]:
    """
    查询 Shell FolderItem 的可用/总空间。

    通过解析 folder_item.GetDetailsOf("可用空间", ...) 等字段获取。
    某些 MTP 设备可能不返回该信息，此时返回 (0, 0)。

    Returns:
        (free_bytes, total_bytes) 元组。
    """
    free_bytes = 0
    total_bytes = 0
    # FolderItem 的 ExtendedProperty / GetDetailsOf 在不同 Windows 版本
    # 和 MTP 驱动上表现不一致，这里做 best-effort 解析。
    try:
        # 尝试通过 Parent Folder 的 GetDetailsOf 获取
        parent = folder_item.Parent
        if parent:
            detail_count = 0
            try:
                # 大部分 Folder 支持到 ~40 个 detail 列
                detail_count = 40
            except Exception:
                pass

            free_str = ""
            total_str = ""
            for i in range(min(detail_count, 40)):
                try:
                    col_name = parent.GetDetailsOf(None, i)
                    if not col_name:
                        continue
                    col_lower = col_name.lower()
                    val = parent.GetDetailsOf(folder_item, i)
                    if val and ("可用" in col_lower or "free" in col_lower):
                        if not free_str:
                            free_str = val
                    elif val and ("总" in col_lower or "total" in col_lower or "容量" in col_lower or "size" in col_lower):
                        if not total_str:
                            total_str = val
                except Exception:
                    continue

            free_bytes = _parse_size_str(free_str)
            total_bytes = _parse_size_str(total_str)
    except Exception:
        pass

    return free_bytes, total_bytes


def _parse_size_str(s: str) -> int:
    """
    解析 Windows Shell 返回的大小字符串。

    支持格式:
      - "1.23 GB" / "510 MB" / "4.5 KB"
      - "1,234,567" (纯字节)
      - "" / 不可解析 → 0
    """
    if not s:
        return 0
    s = s.strip().replace(",", "")
    try:
        return int(s)
    except ValueError:
        pass

    units = {
        "kb": 1024,
        "mb": 1024 ** 2,
        "gb": 1024 ** 3,
        "tb": 1024 ** 4,
        "字节": 1,
        "byte": 1,
    }
    s_lower = s.lower()
    for unit, multiplier in units.items():
        if unit in s_lower:
            num_part = s_lower.replace(unit, "").strip()
            try:
                return int(float(num_part) * multiplier)
            except ValueError:
                pass
    return 0
