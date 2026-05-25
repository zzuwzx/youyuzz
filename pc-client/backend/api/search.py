# 鱿郁仔仔 — 搜索路由
# pc-client/backend/api/search.py

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from scraper.client import GameScraper
from scraper.parser import parse_game_url
from .models import (
    SearchResultItem,
    SearchResponse,
    GameDetailResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局单例 scraper，通过 lifespan 管理生命周期
_scraper: Optional[GameScraper] = None


def set_scraper(scraper: GameScraper) -> None:
    """由 main.py lifespan 注入 scraper 实例。"""
    global _scraper
    _scraper = scraper


# ============================================================
#  GET /api/search
# ============================================================

@router.get("/search", response_model=SearchResponse)
async def search_game(
    keyword: str = Query(..., min_length=1, description="游戏搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
):
    """搜索游戏。"""
    if _scraper is None:
        raise HTTPException(status_code=503, detail="搜索服务未就绪")

    try:
        results = await _scraper.search(keyword, limit=limit)
    except Exception as exc:
        logger.exception("搜索失败: keyword=%r", keyword)
        raise HTTPException(status_code=500, detail=f"搜索服务异常: {exc}")

    items = [
        SearchResultItem(
            title=r.name,
            version=r.version,
            size=None,
            source_url=r.raw_url,
        )
        for r in results
    ]

    return SearchResponse(keyword=keyword, results=items, total=len(items))


# ============================================================
#  GET /api/game/detail
# ============================================================

@router.get("/game/detail", response_model=GameDetailResponse)
async def game_detail(
    url: str = Query(..., min_length=1, description="游戏详情页 URL"),
):
    """获取游戏详情（网盘链接、子文件分类）。"""
    if _scraper is None:
        raise HTTPException(status_code=503, detail="搜索服务未就绪")

    try:
        links, version, has_cheats = parse_game_url(url)

        # 二次访问详情页提取更细粒度信息
        body_url: Optional[str] = None
        update_url: Optional[str] = None
        dlc_url: Optional[str] = None
        cheat_url: Optional[str] = None

        for link in links:
            lurl = link.url
            lname = link.url.lower()
            if link.disk_type.value in ("quark", "baidu", "aliyun"):
                # 每个资源类型的链接相同都指向同一个详情页，
                # 实际下载链接需要转存后才能获取。
                # 这里仅做结构占位，详情页精细化在 Phase 2 实现。
                body_url = lurl

        links_raw = [
            {
                "disk_type": link.disk_type.value,
                "url": link.url,
                "password": link.password,
            }
            for link in links
        ]

        return GameDetailResponse(
            title="",
            body_url=body_url,
            update_url=update_url,
            dlc_url=dlc_url,
            cheat_url=cheat_url,
            links=links_raw,
        )
    except Exception as exc:
        logger.exception("获取游戏详情失败: url=%r", url)
        raise HTTPException(status_code=500, detail=f"详情获取异常: {exc}")
