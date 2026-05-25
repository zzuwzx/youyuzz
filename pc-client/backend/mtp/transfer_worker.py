# -*- coding: utf-8 -*-
"""Background transfer worker for MTP install tasks.

Runs ShellCopyHereBackend.copy_file in a background thread (COM STA apartment).
Updates the shared task store with real-time progress.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import pythoncom

logger = logging.getLogger(__name__)


def run_transfer(
    task_id: str,
    folder_path: str,
    task_store: dict,
    mtp_backend,
) -> None:
    """Run MTP transfer in a background thread.

    Scans the folder for .nsz/.nsp files, transfers each to SD Card install,
    and updates the task store with progress.

    Args:
        task_id:      task identifier in task_store
        folder_path:  path to folder containing game files
        task_store:   shared dict for progress reporting
        mtp_backend:  MTPTransfer instance (ShellCopyHereBackend or WpdBackend)
    """
    from .base import CopyResult, PartitionType
    from api.models import InstallStage

    task = task_store.get(task_id)
    if not task:
        return

    try:
        # Initialize COM for this thread
        pythoncom.CoInitialize()

        # Scan for game files
        folder = Path(folder_path)
        game_files = sorted(
            [p for p in folder.rglob("*") if p.suffix.lower() in (".nsz", ".nsp", ".xci")],
            key=lambda p: p.stat().st_size,
            reverse=True,  # largest first (usually base game)
        )

        if not game_files:
            task["stage"] = InstallStage.FAILED
            task["error"] = "文件夹中没有找到游戏文件 (.nsz/.nsp/.xci)"
            return

        total_files = len(game_files)
        task["stage"] = InstallStage.TRANSFERRING_MTP
        task["total_files"] = total_files
        task["completed_files"] = 0

        # Check device
        if not mtp_backend.is_device_connected():
            task["stage"] = InstallStage.FAILED
            task["error"] = "Switch 未连接——请确认 DBI 已启动并连接 USB"
            return

        for idx, file_path in enumerate(game_files):
            file_name = file_path.name
            file_size = file_path.stat().st_size

            task["current_file"] = file_name
            task["percent"] = 0.0
            task["speed"] = None

            logger.info("[%s] Transferring %d/%d: %s (%.1f MB)",
                        task_id, idx + 1, total_files, file_name, file_size / (1024 * 1024))

            # Progress callback
            last_update = 0.0

            def on_progress(p):
                nonlocal last_update
                now = time.time()
                if now - last_update < 0.2 and p.ratio < 1.0:
                    return  # throttle to ~5 Hz
                last_update = now

                # Update task store
                task["percent"] = round(p.ratio * 100, 1)
                if p.elapsed_sec > 0 and p.bytes_done > 0:
                    speed_mb = p.bytes_done / (p.elapsed_sec * 1024 * 1024)
                    task["speed"] = f"{speed_mb:.1f} MB/s"

            # Do the transfer
            result = mtp_backend.copy_file(
                str(file_path),
                PartitionType.SD_CARD,
                on_progress=on_progress,
            )

            if result != CopyResult.OK:
                task["stage"] = InstallStage.FAILED
                task["error"] = f"传输失败 ({result.name}): {file_name}"
                task["completed_files"] = idx
                return

            task["completed_files"] = idx + 1

        # All done
        task["stage"] = InstallStage.COMPLETED
        task["percent"] = 100.0
        task["current_file"] = None
        task["speed"] = None
        logger.info("[%s] Transfer complete: %d files", task_id, total_files)

    except Exception as e:
        logger.exception("[%s] Transfer worker crashed", task_id)
        task["stage"] = InstallStage.FAILED
        task["error"] = str(e)
    finally:
        pythoncom.CoUninitialize()
