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
    SubTaskProgress,
)

logger = logging.getLogger(__name__)


# MTP backend injection (set by main.py)
_mtp_backend = None

# Scraper injection (set by main.py)
_scraper = None

# Cloud disk injection (set by main.py)
_disk = None

def set_mtp_backend(backend) -> None:
    global _mtp_backend
    _mtp_backend = backend

def set_scraper(scraper) -> None:
    global _scraper
    _scraper = scraper

def set_disk(disk) -> None:
    global _disk
    _disk = disk

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
        "eta": None,
        "total_files": 0,
        "completed_files": 0,
        "error": None,
        "game_url": req.game_url,
        "install_order": req.install_order.value,
    }

    logger.info("安装任务已创建: task_id=%s, url=%s", task_id, req.game_url)

    # 启动异步安装管道
    if _scraper and _disk and _mtp_backend:
        from services.install_pipeline import pipeline
        asyncio.create_task(
            pipeline.run(
                task_id=task_id,
                game_name=req.game_url,
                task_store=_tasks,
                scraper=_scraper,
                disk=_disk,
                mtp_backend=_mtp_backend,
            )
        )
        logger.info("安装管道已启动: task_id=%s", task_id)
    else:
        _tasks[task_id]["stage"] = InstallStage.FAILED
        _tasks[task_id]["error"] = "后端服务未就绪（scraper/disk/mtp 未初始化）"

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

    # 构建子任务进度（批量任务）
    sub_tasks = None
    if "sub_tasks" in task and task["sub_tasks"]:
        sub_tasks = []
        for sub_id in task["sub_tasks"]:
            sub = _tasks.get(sub_id)
            if sub:
                sub_stage = sub["stage"]
                if isinstance(sub_stage, InstallStage):
                    sub_stage = sub_stage.value
                sub_tasks.append(SubTaskProgress(
                    task_id=sub_id,
                    game_name=sub.get("game_name", ""),
                    stage=sub_stage,
                    percent=sub["percent"],
                    error=sub.get("error"),
                ))

    return InstallProgressResponse(
        task_id=task_id,
        stage=task["stage"],
        percent=task["percent"],
        current_file=task["current_file"],
        speed=task["speed"],
        eta=task.get("eta"),
        total_files=task["total_files"],
        completed_files=task["completed_files"],
        error=task["error"],
        sub_tasks=sub_tasks,
    )


# ============================================================
#  GET /api/install/{task_id}/sub_tasks
# ============================================================

@router.get("/install/{task_id}/sub_tasks")
async def install_sub_tasks(task_id: str):
    """返回批量任务中各子任务的进度。"""
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    sub_task_ids = task.get("sub_tasks", [])
    result = []
    for sub_id in sub_task_ids:
        sub = _tasks.get(sub_id)
        if sub:
            sub_stage = sub["stage"]
            if isinstance(sub_stage, InstallStage):
                sub_stage = sub_stage.value
            result.append({
                "task_id": sub_id,
                "game_name": sub.get("game_name", ""),
                "stage": sub_stage,
                "percent": sub["percent"],
                "error": sub.get("error"),
            })

    return {"task_id": task_id, "sub_tasks": result}


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
        "eta": None,
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
    # VIP 检查
    from config import config
    if not config.LICENSE_KEY:
        raise HTTPException(status_code=403, detail="批量安装需要 VIP 授权，请先激活")

    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "stage": InstallStage.QUEUED,
        "percent": 0.0,
        "current_file": None,
        "speed": None,
        "eta": None,
        "total_files": len(req.game_names),
        "completed_files": 0,
        "error": None,
        "game_names": req.game_names,
        "is_batch": True,
        "sub_tasks": [],
    }

    logger.info("批量安装任务已创建: task_id=%s, count=%d", task_id, len(req.game_names))

    # 启动批量安装
    if _scraper and _disk and _mtp_backend:
        from services.batch_manager import batch_manager
        asyncio.create_task(
            batch_manager.run_batch(
                task_id=task_id,
                game_names=req.game_names,
                task_store=_tasks,
                scraper=_scraper,
                disk=_disk,
                mtp_backend=_mtp_backend,
            )
        )
        logger.info("批量安装已启动: task_id=%s", task_id)
    else:
        _tasks[task_id]["stage"] = InstallStage.FAILED
        _tasks[task_id]["error"] = "后端服务未就绪（scraper/disk/mtp 未初始化）"

    return InstallTaskResponse(
        task_id=task_id,
        status="accepted",
        message=f"批量安装 {len(req.game_names)} 个游戏已加入队列",
    )


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

                # 构建子任务进度
                sub_tasks_data = None
                if "sub_tasks" in task and task["sub_tasks"]:
                    sub_tasks_data = []
                    for sub_id in task["sub_tasks"]:
                        sub = _tasks.get(sub_id)
                        if sub:
                            sub_stage = sub["stage"]
                            if isinstance(sub_stage, InstallStage):
                                sub_stage = sub_stage.value
                            sub_tasks_data.append({
                                "task_id": sub_id,
                                "game_name": sub.get("game_name", ""),
                                "stage": sub_stage,
                                "percent": sub["percent"],
                                "error": sub.get("error"),
                            })

                current = {
                    "task_id": task_id,
                    "stage": stage_val,
                    "percent": task["percent"],
                    "current_file": task["current_file"],
                    "speed": task["speed"],
                    "eta": task.get("eta"),
                    "total_files": task["total_files"],
                    "completed_files": task["completed_files"],
                    "error": task["error"],
                }
                if sub_tasks_data:
                    current["sub_tasks"] = sub_tasks_data

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
