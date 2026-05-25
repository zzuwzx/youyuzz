# 鱿郁仔仔 — 安装任务路由
# pc-client/backend/api/install.py

from __future__ import annotations

import asyncio
import json
import logging
import uuid
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .models import (
    InstallRequest,
    LocalInstallRequest,
    BatchInstallRequest,
    InstallProgressResponse,
    InstallTaskResponse,
    InstallStage,
)

logger = logging.getLogger(__name__)


# MTP backend injection (set by main.py)
_mtp_backend = None

def set_mtp_backend(backend) -> None:
    global _mtp_backend
    _mtp_backend = backend

router = APIRouter()

# 内存任务存储（Phase 1；Phase 2 可迁移到 SQLite）
_tasks: dict[str, dict] = {}


def get_task_store() -> dict:
    return _tasks


# ============================================================
#  POST /api/install
# ============================================================

@router.post("/install", response_model=InstallTaskResponse, status_code=202)
async def start_install(req: InstallRequest):
    """启动远程安装任务。"""
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "stage": InstallStage.QUEUED,
        "percent": 0.0,
        "current_file": None,
        "speed": None,
        "total_files": 0,
        "completed_files": 0,
        "error": None,
        "game_url": req.game_url,
        "install_order": req.install_order.value,
    }

    logger.info("安装任务已创建: task_id=%s, url=%s", task_id, req.game_url)

    # Phase 2: 实际启动异步安装流程
    # asyncio.create_task(_run_install_pipeline(task_id, req))

    return InstallTaskResponse(
        task_id=task_id,
        status="accepted",
        message="安装任务已加入队列",
    )


# ============================================================
#  GET /api/install/{task_id}/progress
# ============================================================

@router.get("/install/{task_id}/progress", response_model=InstallProgressResponse)
async def install_progress(task_id: str):
    """查询安装任务进度。"""
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return InstallProgressResponse(
        task_id=task_id,
        stage=task["stage"],
        percent=task["percent"],
        current_file=task["current_file"],
        speed=task["speed"],
        total_files=task["total_files"],
        completed_files=task["completed_files"],
        error=task["error"],
    )


# ============================================================
#  POST /api/install/local
# ============================================================

@router.post("/install/local", response_model=InstallTaskResponse, status_code=202)
async def start_local_install(req: LocalInstallRequest):
    """启动本地离线安装任务。"""
    folder = Path(req.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"文件夹不存在: {req.folder_path}")

    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "stage": InstallStage.QUEUED,
        "percent": 0.0,
        "current_file": None,
        "speed": None,
        "total_files": 0,
        "completed_files": 0,
        "error": None,
        "folder_path": req.folder_path,
        "is_local": True,
    }

    logger.info("本地安装任务已创建: task_id=%s, path=%s", task_id, req.folder_path)

    # Start background transfer
    if _mtp_backend is not None:
        from mtp.transfer_worker import run_transfer
        t = threading.Thread(
            target=run_transfer,
            args=(task_id, req.folder_path, _tasks, _mtp_backend),
            daemon=True,
        )
        t.start()
        logger.info("后台传输线程已启动: task_id=%s", task_id)
    else:
        _tasks[task_id]["stage"] = InstallStage.FAILED
        _tasks[task_id]["error"] = "MTP 后端未初始化"
    return InstallTaskResponse(task_id=task_id, status="accepted", message="本地安装任务已加入队列")


# ============================================================
#  POST /api/install/batch (VIP)
# ============================================================

@router.post("/install/batch", response_model=InstallTaskResponse, status_code=202)
async def start_batch_install(req: BatchInstallRequest):
    """批量安装（VIP）。"""
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "stage": InstallStage.QUEUED,
        "percent": 0.0,
        "current_file": None,
        "speed": None,
        "total_files": len(req.game_list),
        "completed_files": 0,
        "error": None,
        "game_list": [g.game_url for g in req.game_list],
        "is_batch": True,
    }

    logger.info("批量安装任务已创建: task_id=%s, count=%d", task_id, len(req.game_list))
    return InstallTaskResponse(task_id=task_id, status="accepted", message=f"批量安装 {len(req.game_list)} 个游戏已加入队列")


# ============================================================
#  GET /api/install/{task_id}/stream  (SSE 实时进度推送)
# ============================================================

@router.get("/install/{task_id}/stream")
async def install_stream(task_id: str, request: Request):
    """SSE 流式推送安装进度，替代轮询。

    连接建立后立即推送当前进度，后续每 500ms 轮询
    任务状态，仅在进度数据变化时推送新事件。
    终端状态（completed / failed / cancelled）发送 done
    事件后关闭流。
    """
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    async def event_generator():
        last_sent: dict | None = None

        # SSE 初始握手：告知前端重连间隔 1000ms
        yield "retry: 1000\n\n"

        try:
            while True:
                # 检查客户端是否已断开
                if await request.is_disconnected():
                    logger.debug("SSE 客户端断开: task_id=%s", task_id)
                    return

                task = _tasks.get(task_id)
                if task is None:
                    yield f"event: error\ndata: {json.dumps({'error': '任务已清理'}, ensure_ascii=False)}\n\n"
                    return

                # 构建当前进度快照
                stage_val = task["stage"]
                if isinstance(stage_val, InstallStage):
                    stage_val = stage_val.value

                current = {
                    "task_id": task_id,
                    "stage": stage_val,
                    "percent": task["percent"],
                    "current_file": task["current_file"],
                    "speed": task["speed"],
                    "total_files": task["total_files"],
                    "completed_files": task["completed_files"],
                    "error": task["error"],
                }

                # 仅在进度变化时推送
                if current != last_sent:
                    yield f"data: {json.dumps(current, ensure_ascii=False)}\n\n"
                    last_sent = current

                # 终端状态：发送 done 后关闭流
                if stage_val in ("completed", "failed", "cancelled"):
                    yield f"event: done\ndata: {json.dumps({'done': True, 'stage': stage_val}, ensure_ascii=False)}\n\n"
                    return

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.debug("SSE 流被取消: task_id=%s", task_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
