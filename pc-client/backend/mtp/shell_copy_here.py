"""
ShellCopyHere 后端 — 基于 win32com Shell.Application + CopyHere(1556)

直接复用 SquidInstallerGUI.py 验证过的 MTP 传输方案:
  - Shell.Application Dispatch → NameSpace(17) 枚举设备
  - CopyHere(local_shell_item, 1556) 静默拷贝
  - 阻尼对数进度模拟（30 FPS 高频刷新）
  - 弹窗杀手：自动隐藏 CopyHere 产生的进度窗口

CopyHere flags 说明 (1556):
  4    = FOF_SILENT          — 不显示进度对话框
  16   = FOF_NOCONFIRMATION   — 不确认覆盖
  512  = FOF_NOCONFIRMMKDIR   — 不确认创建目录
  1024 = FOF_NOERRORUI        — 不显示错误 UI
  ────
  1556

适用场景: Phase 1 快速上线，由 IFileOperationBackend 逐步替代以获取真实进度。
"""
import logging
import math
import os
import threading
import re
import time
from typing import Optional

import pythoncom
import win32com.client
import win32gui
import win32con
import ctypes

from .base import (
    MTPTransfer, PartitionType, PartitionInfo, CopyResult,
    TransferProgress, ProgressCallback,
)
from .dbi_discovery import DBIDiscoveryError, discover_partitions

logger = logging.getLogger(__name__)


# ── 常量 ──────────────────────────────────────────────
COPY_FLAGS_SILENT = 1556   # FOF_SILENT | NOCONFIRMATION | NOCONFIRMMKDIR | NOERRORUI
COPY_FLAGS = 1556           # compatible: old silent-mode refs
COPY_FLAGS_WITH_DIALOG = 528  # NOCONFIRMATION|NOCONFIRMMKDIR|NOERRORUI (no FOF_SILENT)
SSF_DRIVES = 17            # Shell NameSpace: 我的电脑
SWITCH_MARKER = "Switch"
SD_INSTALL_MARKER = "SD Card install"
NAND_INSTALL_MARKER = "NAND install"
CHEAT_MARKERS = ("金手指", "cheat")
POPUP_CHECK_INTERVAL = 0.01  # 秒 — 弹窗检测频率


class ShellCopyHereBackend(MTPTransfer):
    """
    Phase 1 快速上线后端。

    复用 SquidInstallerGUI.py 中已验证的 win32com Shell.Application 方案。
    进度为阻尼模拟值（非真实 MTP 进度），由 IFileOperationBackend 替代后
    可获取原生 Advise 回调进度。
    """

    def __init__(self):
        self._shell_app = None
        self._partitions: dict[PartitionType, PartitionInfo] = {}
        self._stop_popup_killer = threading.Event()
        self._popup_killer_thread: Optional[threading.Thread] = None

    # ── 设备发现 ──────────────────────────────────────

    def is_device_connected(self) -> bool:
        try:
            self._ensure_shell()
            partitions = discover_partitions(shell_app=self._shell_app)
            return PartitionType.SD_CARD in partitions or PartitionType.NAND in partitions
        except DBIDiscoveryError:
            return False
        except Exception:
            return False

    def discover_partitions(self) -> dict[PartitionType, PartitionInfo]:
        self._ensure_shell()
        self._partitions = discover_partitions(shell_app=self._shell_app)
        return self._partitions

    # ── 文件传输 ──────────────────────────────────────

    def copy_file(
        self,
        source: str,
        partition: PartitionType = PartitionType.SD_CARD,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> CopyResult:
        if not os.path.isfile(source):
            logger.error("源文件不存在: %s", source)
            return CopyResult.IO_ERROR

        file_size = os.path.getsize(source)

        # 1. 确保设备在线 & 分区可用
        try:
            self._ensure_shell()
            if not self._partitions:
                self.discover_partitions()
            pi = self._partitions.get(partition)
            if pi is None:
                logger.error("目标分区不可用: %s", partition.name)
                return CopyResult.PARTITION_NOT_FOUND
        except DBIDiscoveryError:
            return CopyResult.DEVICE_NOT_FOUND

        # 2. 空间检查
        if file_size > pi.free_bytes > 0:
            logger.warning(
                "空间不足: 需要 %d MB, 可用 %d MB",
                file_size // (1024 * 1024), pi.free_bytes // (1024 * 1024),
            )
            return CopyResult.NO_SPACE

        # 3. 执行 CopyHere
        try:
            install_folder = self._resolve_install_folder(partition)
            if install_folder is None:
                return CopyResult.PARTITION_NOT_FOUND

            pythoncom.CoInitialize()
            self._start_popup_killer()
            self._do_copyhere(source, install_folder)

            # 4. 进度监控
            self._monitor_dialog_progress(file_size, on_progress)

            logger.info("传输完成: %s -> %s", source, pi.name)
            return CopyResult.OK

        except Exception as e:
            logger.exception("CopyHere 传输异常: %s", e)
            return CopyResult.COPY_FAILED
        finally:
            self._stop_popup_killer.set()

    # -- 存储查询 --

    def get_free_space(self, partition: PartitionType) -> int:
        try:
            self._ensure_shell()
            if not self._partitions:
                self.discover_partitions()
            pi = self._partitions.get(partition)
            return pi.free_bytes if pi else -1
        except Exception:
            return -1

    # -- 内部方法 --

    def _ensure_shell(self):
        """Lazy init Shell.Application COM object."""
        if self._shell_app is None:
            pythoncom.CoInitialize()
            self._shell_app = win32com.client.Dispatch("Shell.Application")

    def _resolve_install_folder(self, partition: PartitionType):
        """Locate DBI install target folder via Shell NameSpace.

        Enumerates Switch device children, matching "5: SD Card install" or "6: NAND install".
        """
        my_computer = self._shell_app.NameSpace(SSF_DRIVES)
        for item in my_computer.Items():
            if SWITCH_MARKER in item.Name:
                switch_folder = item.GetFolder
                for sub in switch_folder.Items():
                    name = sub.Name
                    if partition == PartitionType.SD_CARD:
                        if SD_INSTALL_MARKER in name:
                            return sub.GetFolder
                    elif partition == PartitionType.NAND:
                        if NAND_INSTALL_MARKER in name:
                            return sub.GetFolder
                break
        return None

    def _do_copyhere(self, source: str, dest_folder):
        """Execute CopyHere with dialog-allowing flags.

        Args:
            source:       absolute local file path
            dest_folder:  target Shell Folder object
        """
        source_dir = os.path.dirname(source)
        source_name = os.path.basename(source)
        local_folder = self._shell_app.NameSpace(source_dir)
        local_item = local_folder.ParseName(source_name)

        if local_item is None:
            raise FileNotFoundError(f"Cannot resolve source via Shell: {source}")

        dest_folder.CopyHere(local_item, COPY_FLAGS_WITH_DIALOG)

    # -- 弹窗杀手 --

    def _start_popup_killer(self):
        """Start background thread to auto-hide CopyHere progress windows."""
        self._stop_popup_killer.clear()
        self._popup_killer_thread = threading.Thread(
            target=self._popup_killer_worker, daemon=True,
        )
        self._popup_killer_thread.start()

    def _popup_killer_worker(self):
        """High-frequency top-level window enumeration to hide copy progress popups.

        Match conditions:
          - Class: "OperationStatusWindow" or "#32770"
          - Title contains: copy-related keywords
          - Title does NOT contain: app name (avoid self-kill)

        Action:
          - WS_EX_LAYERED + LWA_ALPHA=0 for full transparency
          - Move off-screen (-35000, -35000)
          - SW_HIDE
        """
        pythoncom.CoInitialize()
        try:
            while not self._stop_popup_killer.is_set():
                try:
                    win32gui.EnumWindows(self._popup_enum_callback, None)
                except Exception:
                    pass
                time.sleep(POPUP_CHECK_INTERVAL)
                pythoncom.PumpWaitingMessages()
        finally:
            pythoncom.CoUninitialize()
    def _popup_enum_callback(self, hwnd, _extra):
        if not win32gui.IsWindow(hwnd):
            return True
        try:
            class_name = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True

        if class_name not in ("OperationStatusWindow", "#32770"):
            return True
        if not any(k in title for k in ("\u590d\u5236", "Copy", "Switch", "\u6b63\u5728", "Moving")):
            return True
        if "\u9c7f\u90c1\u4ed4\u4ed4" in title:
            return True

        # Hide the popup
        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED)
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
            win32gui.SetWindowPos(
                hwnd, None, -35000, -35000, 10, 10,
                win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
            )
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        except Exception:
            pass
        return True

    # -- dialog progress monitoring --

    _PROGRESS_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
    _PROGRESS_REMAIN_RE = re.compile(r"\u5269\u4f59.*?(\d+)\s*(?:\u79d2|s)", re.IGNORECASE)
    _PROGRESS_ENGLISH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:complete|done)", re.IGNORECASE)

    def _find_dialog_hwnd(self):
        """Find the current copy progress dialog HWND; returns None if not found."""
        result = {"hwnd": None}

        def _find(hwnd, _extra):
            if not win32gui.IsWindow(hwnd):
                return True
            try:
                cn = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
            except Exception:
                return True
            if cn in ("OperationStatusWindow", "#32770") and any(
                k in title for k in ("\u590d\u5236", "Copy", "Switch", "\u6b63\u5728", "Moving")
            ):
                result["hwnd"] = hwnd
                return False
            return True

        try:
            win32gui.EnumWindows(_find, None)
        except Exception:
            pass
        return result["hwnd"]

    def _find_progress_bar(self, dialog_hwnd):
        """Find the msctls_progress32 child window inside the copy dialog."""
        result = {"hwnd": None}

        def _find(hwnd, _extra):
            try:
                if win32gui.GetClassName(hwnd) == "msctls_progress32":
                    result["hwnd"] = hwnd
                    return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(dialog_hwnd, _find, None)
        except Exception:
            pass
        return result["hwnd"]

    def _read_dialog_progress(self, hwnd, prog_hwnd=None):
        """Read progress from the copy dialog.

        Priority: SendMessage(PBM_GETPOS) on msctls_progress32 > window text parsing.
        Args:
            hwnd: dialog HWND
            prog_hwnd: cached progress bar HWND (optional, for performance)
        Returns (ratio 0.0~1.0, raw_text) or (None, None).
        """
        # Strategy 1: SendMessage on progress bar (most reliable)
        if prog_hwnd is None:
            prog_hwnd = self._find_progress_bar(hwnd)

        if prog_hwnd is not None:
            try:
                pos = self._user32.SendMessageW(prog_hwnd, self._PBM_GETPOS, 0, 0)
                high = self._user32.SendMessageW(prog_hwnd, self._PBM_GETRANGE, 0, 0)
                if high > 0:
                    ratio = min(pos / high, 1.0)
                    return (ratio, f"PBM pos={pos} high={high}")
            except Exception:
                pass

        # Strategy 2: window text parsing (fallback)
        texts = []

        def _child_enum(h, _extra):
            try:
                cn = win32gui.GetClassName(h)
                txt = win32gui.GetWindowText(h)
                if txt and txt.strip():
                    texts.append((cn, txt.strip()))
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(hwnd, _child_enum, None)
        except Exception:
            pass

        try:
            title = win32gui.GetWindowText(hwnd)
            if title:
                texts.append(("TitleBar", title))
        except Exception:
            pass

        for class_name, text in texts:
            m = self._PROGRESS_PCT_RE.search(text)
            if m:
                pct = float(m.group(1))
                return (min(pct / 100.0, 1.0), text)

        return (None, None)

    def _hide_dialog(self, hwnd):
        """Hide progress dialog: transparent + off-screen + SW_HIDE."""
        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED)
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
            win32gui.SetWindowPos(
                hwnd, None, -35000, -35000, 10, 10,
                win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
            )
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        except Exception:
            pass

    def _damped_progress_tick(self, file_size, on_progress, start_time):
        """One tick of damped log simulation (fallback). Returns True to continue."""
        size_mb = file_size / (1024 * 1024)
        expected_sec = max(1.5, size_mb / 28.0)
        elapsed = time.time() - start_time
        target = 1.0 - math.exp(-2.2 * (elapsed / expected_sec))
        if target > 0.95:
            target = 0.95 + (1.0 - math.exp(-0.2 * (elapsed / expected_sec))) * 0.04
        ratio = min(0.96, target)
        progress = TransferProgress(
            bytes_total=file_size, bytes_done=int(file_size * ratio),
            ratio=ratio, elapsed_sec=elapsed,
            eta_sec=max(0, expected_sec - elapsed),
        )
        on_progress(progress)
        return True

    def _monitor_dialog_progress(self, file_size, on_progress):
        """Monitor Windows copy progress dialog for real progress.

        Uses SendMessage(PBM_GETPOS) on msctls_progress32 for real progress.
        Falls back to damped simulation if progress bar unavailable.
        """
        if on_progress is None:
            wait_sec = max(1.5, file_size / (28 * 1024 * 1024))
            time.sleep(wait_sec)
            return

        start_time = time.time()
        dialog_hwnd = None
        prog_hwnd = None

        # Phase 1: wait for dialog (up to 10 seconds)
        wait_start = time.time()
        while time.time() - wait_start < 10.0:
            hwnd = self._find_dialog_hwnd()
            if hwnd is not None:
                dialog_hwnd = hwnd
                self._hide_dialog(dialog_hwnd)
                # Cache the progress bar HWND
                prog_hwnd = self._find_progress_bar(dialog_hwnd)
                if prog_hwnd:
                    logger.debug("Progress dialog hwnd=%d progbar=%d found", dialog_hwnd, prog_hwnd)
                else:
                    logger.debug("Progress dialog hwnd=%d (no msctls_progress32)", dialog_hwnd)
                break
            time.sleep(0.5)
            pythoncom.PumpWaitingMessages()

        # Phase 2: monitoring loop
        if dialog_hwnd is not None:
            last_ratio = 0.0
            while True:
                if not win32gui.IsWindow(dialog_hwnd):
                    break

                ratio, raw_text = self._read_dialog_progress(dialog_hwnd, prog_hwnd)

                if ratio is not None:
                    last_ratio = max(last_ratio, ratio)
                    elapsed = time.time() - start_time
                    progress = TransferProgress(
                        bytes_total=file_size, bytes_done=int(file_size * last_ratio),
                        ratio=last_ratio, elapsed_sec=elapsed, eta_sec=-1.0,
                    )
                    on_progress(progress)
                else:
                    # No progress data -> damped simulation
                    self._damped_progress_tick(file_size, on_progress, start_time)

                time.sleep(0.5)
                pythoncom.PumpWaitingMessages()
        else:
            # Dialog never appeared -> pure damped simulation
            logger.debug("Progress dialog not found, fallback to damped simulation")
            elapsed = time.time() - start_time
            expected = max(1.5, (file_size / (1024 * 1024)) / 28.0)
            while elapsed < expected + 30:
                self._damped_progress_tick(file_size, on_progress, start_time)
                time.sleep(0.5)
                pythoncom.PumpWaitingMessages()
                elapsed = time.time() - start_time

        # Final alignment
        final = TransferProgress(
            bytes_total=file_size, bytes_done=file_size,
            ratio=1.0, elapsed_sec=time.time() - start_time, eta_sec=0,
        )
        on_progress(final)

    def _is_copy_window_alive(self) -> bool:
        """检查是否还有 CopyHere 进度窗口存活。"""
        result = {"alive": False}

        def _check(hwnd, _extra):
            if not win32gui.IsWindow(hwnd):
                return True
            try:
                cn = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
            except Exception:
                return True
            if cn in ("OperationStatusWindow", "#32770") and any(
                k in title for k in ("复制", "Copy", "Switch", "正在", "Moving")
            ):
                result["alive"] = True
                return False  # 找到即停止枚举
            return True

        try:
            win32gui.EnumWindows(_check, None)
        except Exception:
            pass
        return result["alive"]
