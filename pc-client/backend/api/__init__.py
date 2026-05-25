# 鱿郁仔仔 — API 路由聚合
# pc-client/backend/api/__init__.py

from fastapi import APIRouter

from .search import router as search_router
from .install import router as install_router
from .device import router as device_router
from .settings import router as settings_router
from .system import router as system_router

# 聚合路由，统一加 /api 前缀
api_router = APIRouter(prefix="/api")
api_router.include_router(search_router, tags=["search"])
api_router.include_router(install_router, tags=["install"])
api_router.include_router(device_router, tags=["device"])
api_router.include_router(settings_router, tags=["settings"])
api_router.include_router(system_router, tags=["system"])

__all__ = ["api_router"]
