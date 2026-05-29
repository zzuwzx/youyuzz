# 鱿郁仔仔 — FastAPI 本地服务入口
# pc-client/backend/main.py
#
# 启动:  uvicorn main:app --host 127.0.0.1 --port 18888 --reload
# 或直接: python main.py

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import sys
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config
from api import api_router
from api.models import ErrorResponse
from services.auto_updater import AutoUpdater
from services.lan_accelerator import get_accelerator

# ============================================================
#  日志配置
# ============================================================

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-5s | %(name)s:%(lineno)d | %(message)s"
)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        root.addHandler(console)

    log_dir = config.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "backend.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(file_handler)

    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging initialized (level=%s)", config.LOG_LEVEL)


# ============================================================
#  心跳后台任务
# ============================================================

async def _heartbeat_loop() -> None:
    logger = logging.getLogger(__name__)
    interval = 3600
    while True:
        await asyncio.sleep(interval)
        if not config.LICENSE_KEY:
            continue
        try:
            from auth.client import heartbeat, get_device_id
            await heartbeat(config.LICENSE_KEY, get_device_id())
            logger.debug("心跳上报成功")
        except Exception:
            logger.warning("心跳上报失败，已静默忽略", exc_info=True)


# ============================================================
#  网盘实例初始化
# ============================================================

def _init_cloud_disk():
    """尝试加载已保存的 cookie 并创建网盘实例。"""
    import json as _json
    cookie_dir = config.DISK_COOKIE_DIR
    # 按优先级尝试: 夸克 → 百度 → 阿里云
    for disk_name, disk_cls_name in [
        ("quark", "QuarkDisk"),
        ("baidu", "BaiduDisk"),
        ("aliyun", "AliyunDisk"),
    ]:
        cookie_file = cookie_dir / f"{disk_name}.json"
        if cookie_file.exists():
            try:
                data = _json.loads(cookie_file.read_text(encoding="utf-8"))
                cookie = data.get("cookie", "")
                if cookie:
                    from cloud_disk import create_disk, DiskType
                    disk_type = DiskType(disk_name)
                    disk = create_disk(disk_type)
                    disk.set_cookie(cookie)
                    return disk
            except Exception:
                pass
    return None



# ============================================================
#  后台更新检查
# ============================================================

async def _check_update_background(updater: AutoUpdater) -> None:
    """后台检查更新，不阻塞启动"""
    logger = logging.getLogger(__name__)
    try:
        # 等待 30 秒后检查，避免阻塞启动
        await asyncio.sleep(30)
        
        has_update, update_info = await updater.check_update()
        if has_update and update_info:
            logger.info("发现新版本: %s", update_info.version)
            # 这里可以发送通知给前端，但不自动安装
            # 用户可以在设置页面手动触发更新
        else:
            logger.debug("当前已是最新版本")
    except Exception:
        logger.debug("后台更新检查失败", exc_info=True)
# ============================================================
#  应用生命周期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    heartbeat_task: asyncio.Task | None = None

    logger.info("鱿郁仔仔 v%s 启动中...", config.VERSION)
    
    # 初始化局域网加速器
    try:
        accelerator = get_accelerator()
        status = accelerator.get_status()
        logger.info("局域网加速器已初始化: is_lan=%s, active_url=%s", 
                    status["is_lan"], status["active_url"])
    except Exception:
        logger.warning("局域网加速器初始化失败", exc_info=True)
    
    # 初始化自动更新器
    try:
        updater = AutoUpdater(current_version=config.VERSION)
        # 后台检查更新（不阻塞启动）
        asyncio.create_task(_check_update_background(updater))
        logger.info("自动更新器已初始化")
    except Exception:
        logger.warning("自动更新器初始化失败", exc_info=True)

    # 初始化 PushDeer 通知器
    try:
        from notifications.pushdeer import notifier
        # 从持久化设置中加载 pushdeer_key
        import json as _json
        settings_file = config.DATA_DIR / "settings.json"
        if settings_file.exists():
            try:
                persisted = _json.loads(settings_file.read_text(encoding="utf-8"))
                key = persisted.get("pushdeer_key", "")
                if key:
                    notifier.update_key(key)
                    logger.info("PushDeer 通知器已初始化 (key=%s...)", key[:6])
            except Exception:
                pass
    except Exception:
        logger.warning("PushDeer 通知器初始化失败", exc_info=True)

    # 初始化爬虫
    scraper = None
    try:
        from scraper.client import GameScraper
        scraper = GameScraper(headless=config.SCRAPER_HEADLESS)
        await scraper.start()
        from api.search import set_scraper
        set_scraper(scraper)
        from api.install import set_scraper as set_install_scraper
        set_install_scraper(scraper)
        logger.info("GameScraper 已就绪 (headless=%s)", config.SCRAPER_HEADLESS)
    except Exception:
        logger.exception("GameScraper 启动失败，搜索接口将不可用")

    # 初始化 MTP 后端
    try:
        backend_name = config.MTP_PREFERRED_BACKEND
        if backend_name == "wpd":
            from mtp import WpdBackend
            mtp = WpdBackend()
        elif backend_name == "shell":
            from mtp import ShellCopyHereBackend
            mtp = ShellCopyHereBackend()
        elif backend_name == "ifileoperation":
            from mtp import IFileOperationBackend
            mtp = IFileOperationBackend()
        else:
            mtp = None
            logger.warning("未知的 MTP 后端: %s", backend_name)
        if mtp:
            from api.device import set_mtp_backend
            set_mtp_backend(mtp)
            from api.install import set_mtp_backend as set_install_mtp_backend
            set_install_mtp_backend(mtp)
            logger.info("MTP 后端已就绪: %s", backend_name)
    except Exception:
        logger.exception("MTP 后端初始化失败，设备检测接口将返回默认值")

    # 初始化网盘实例
    try:
        disk = _init_cloud_disk()
        if disk:
            from api.install import set_disk
            set_disk(disk)
            logger.info("网盘实例已就绪: %s", type(disk).__name__)
        else:
            logger.info("未找到已保存的网盘 cookie，网盘功能需用户先登录")
    except Exception:
        logger.warning("网盘实例初始化失败", exc_info=True)

    # 启动心跳
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    logger.info("授权心跳后台任务已启动 (interval=%ss)", 3600)
    logger.info("服务已启动: http://%s:%s", config.HOST, config.PORT)

    yield

    logger.info("正在关闭服务...")
    if heartbeat_task and not heartbeat_task.done():
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("授权心跳后台任务已停止")

    try:
        import api.search as search_mod
        if search_mod._scraper:
            await search_mod._scraper.stop()
            logger.info("GameScraper 已关闭")
    except Exception:
        pass

    logger.info("服务已关闭")


# ============================================================
#  应用实例
# ============================================================

app = FastAPI(
    title="鱿郁仔仔 API",
    version=config.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def error_handler_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logging.getLogger(__name__).exception(
            "未捕获异常: %s %s", request.method, request.url.path
        )
        response = JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="内部服务错误",
                detail=traceback.format_exc() if config.LOG_LEVEL.upper() == "DEBUG" else None,
                code=500,
            ).model_dump(),
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    logging.getLogger("api.access").info(
        "%s %s -> %d (%.1fms)",
        request.method, request.url.path,
        response.status_code, elapsed_ms,
    )
    return response


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    setup_logging()
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level=config.LOG_LEVEL.lower(),
    )
