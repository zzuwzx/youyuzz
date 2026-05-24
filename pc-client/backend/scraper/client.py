"""Playwright 浏览器客户端 + Vue 数据提取。

核心思路：
  - 不解析 DOM，直接从 Vue 组件树读取 gameList 数据
  - 突破点：root.$children[0].gameList

用法:
    async with GameScraper() as scraper:
        results = await scraper.search("塞尔达")
        for r in results:
            print(r.name, r.links)
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, Page

from .parser import parse_game_url
from .game_dict import GameNameDict
from .models import GameSearchResult

logger = logging.getLogger(__name__)

# Vue 数据提取 JS
EXTRACT_GAMELIST_JS = """() => {
    try {
        const root = document.querySelector('#app').__vue__;
        function findList(comp, depth) {
            if (!comp || depth > 30) return null;
            for (let k in comp) {
                if (k.startsWith('$') || k.startsWith('_')) continue;
                if (typeof comp[k] === 'function') continue;
                const v = comp[k];
                if (Array.isArray(v) && v.length > 0 && v[0]
                    && typeof v[0] === 'object' && v[0].name && v[0].url) {
                    return v.map(item => ({
                        name: item.name || '',
                        url: item.url || '',
                        picUrl: item.picUrl || null,
                        videoUrl: item.videoUrl || null,
                        password: item.password || null
                    }));
                }
            }
            if (comp.$children) {
                for (let c of comp.$children) {
                    const r = findList(c, depth + 1);
                    if (r) return r;
                }
            }
            return null;
        }
        const list = findList(root, 0);
        return list || [];
    } catch(e) {
        return {error: e.message};
    }
}"""

SITE_URL = "https://nsthwj.cn/#/switch"


class GameScraper:
    """nsthwj.cn 游戏检索器。

    Attributes:
        name_dict: 游戏名模糊匹配词典（持久化）
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.name_dict = GameNameDict()
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self):
        """启动浏览器。"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )
        logger.info("Browser started (headless=%s)", self.headless)

    async def stop(self):
        """关闭浏览器。"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    async def search(
        self,
        keyword: str,
        limit: int = 10,
        timeout: int = 15000,
    ) -> list[GameSearchResult]:
        """搜索游戏。

        Args:
            keyword: 搜索关键词
            limit: 最大结果数
            timeout: 页面加载超时(ms)

        Returns:
            搜索结果列表，按相似度排序
        """
        if not self._browser:
            raise RuntimeError("Scraper not started. Call start() first.")

        page: Page = await self._browser.new_page()

        try:
            await page.goto(SITE_URL, timeout=timeout)
            await page.wait_for_timeout(1500)

            # 输入关键词触发 Vue 搜索
            search_input = page.locator("input.el-input__inner")
            await search_input.fill(keyword)
            await search_input.press("Enter")
            await page.wait_for_timeout(2500)  # Wait for Vue reactivity + filter

            # 从 Vue 组件树提取数据
            raw_list = await page.evaluate(EXTRACT_GAMELIST_JS)

            if isinstance(raw_list, dict) and "error" in raw_list:
                logger.error("Vue extraction error: %s", raw_list["error"])
                return []

            # 转换为 SearchResult
            results: list[GameSearchResult] = []
            for item in raw_list:
                name = item.get("name", "")
                raw_url = item.get("url", "")

                # 解析网盘链接
                links, version, has_cheats = parse_game_url(raw_url)

                # 拆分中英文名
                name_cn, _, name_en = name.partition("|")

                # 计算相似度
                similarity = self._calc_similarity(keyword, name)

                result = GameSearchResult(
                    name=name,
                    name_cn=name_cn.strip(),
                    name_en=name_en.strip(),
                    image_url=item.get("picUrl"),
                    video_url=item.get("videoUrl"),
                    links=links,
                    version=version,
                    has_cheats=has_cheats,
                    raw_url=raw_url,
                    similarity=similarity,
                )
                results.append(result)

                # 学习游戏名
                self.name_dict.learn(name)

            # 按相似度排序（越高越好）
            results.sort(key=lambda r: r.similarity, reverse=True)
            results = results[:limit]

            logger.info("Search '%s' -> %d results", keyword, len(results))
            return results

        finally:
            await page.close()

    @staticmethod
    def _calc_similarity(query: str, name: str) -> float:
        """计算搜索词与游戏名的相似度（0-1）。"""
        q = query.lower().strip()
        n = name.lower()
        if q == n:
            return 1.0
        if q in n:
            return 0.85 - len(q) / len(n) * 0.15
        # 模糊匹配：每个字符都在 name 中出现
        matches = sum(1 for c in q if c in n)
        if len(q) > 0:
            return matches / len(q) * 0.6
        return 0.0

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
