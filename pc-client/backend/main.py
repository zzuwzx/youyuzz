# 鱿郁仔仔 — FastAPI 本地服务入口
# pc-client/backend/main.py
#
# 启动:  uvicorn main:app --host 127.0.0.1 --port 18888 --reload
# 或直接: python main.py

from __future__ import annotations

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

# ============================================================
#  日志配置
# ============================================================

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-5s | %(name)s:%(lineno)d | %(message)s"
)

def setup_logging() -> None:
    """配置双通道日志：控制台 + 按天轮转文件。"""
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    # 控制台（uvicorn 已接管 stdout，所以用 stderr 避免干扰）
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        root.addHandler(console)

    # 文件（按天轮转，保留 7 天）
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

    # 抑制过于啰嗦的第三方 logger
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized (level=%s)", config.LOG_LEVEL)


# ============================================================
#  应用生命周期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理跨请求的单例资源（scraper、MTP backend）。"""
    logger = logging.getLogger(__name__)

    # -- 启动阶段 --
    logger.info("鱿郁仔仔 v%s 启动中...", config.VERSION)

    # 初始化 Scraper（注入给 search 路由）
    try:
        from scraper.client import GameScraper
        scraper = GameScraper(headless=config.SCRAPER_HEADLESS)
        await scraper.start()
        from api.search import set_scraper
        set_scraper(scraper)
        logger.info("GameScraper 已就绪 (headless=%s)", config.SCRAPER_HEADLESS)
    except Exception:
        logger.exception("GameScraper 启动失败，搜索接口将不可用")

    # 初始化 MTP 后端（注入给 device 路由）
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

    logger.info("服务已启动: http://%s:%s", config.HOST, config.PORT)

    yield  # <-- 服务运行中

    # -- 关闭阶段 --
    logger.info("正在关闭服务...")
    try:
        from api.search import set_scraper
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

# -- CORS --
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],               # 本地服务，全放行
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- 统一错误处理中间件 --
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
        "%s %s → %d (%.1fms)",
        request.method, request.url.path,
        response.status_code, elapsed_ms,
    )
    return response


# -- 注册路由 --
app.include_router(api_router)


# ============================================================
#  直接运行入口
# ============================================================

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
