"""游戏名模糊匹配词典。

支持别名/简称/不完整名称 → 标准游戏名的映射。
"""

import re
import logging

logger = logging.getLogger(__name__)


class GameNameDict:
    """游戏名称词典，支持别名和模糊匹配。

    用法:
        gd = GameNameDict()
        gd.add_alias("野炊", "塞尔达传说：旷野之息")
        matches = gd.search("塞尔达")
        # -> [("塞尔达传说：王国之泪", 0.33), ("塞尔达传说：旷野之息", 0.40), ...]
    """

    def __init__(self):
        self._aliases: dict[str, str] = {}
        self._known_games: set[str] = set()
        self._init_builtin()

    def _init_builtin(self):
        """内置热门游戏别名。"""
        builtins = {
            # 塞尔达系列
            "野炊": "塞尔达传说：旷野之息",
            "旷野之息": "塞尔达传说：旷野之息",
            "botw": "塞尔达传说：旷野之息",
            "王泪": "塞尔达传说：王国之泪",
            "王国之泪": "塞尔达传说：王国之泪",
            "totk": "塞尔达传说：王国之泪",
            "织梦岛": "塞尔达传说：织梦岛",
            "天剑": "塞尔达传说：御天之剑",
            "御天之剑": "塞尔达传说：御天之剑",

            # 马力欧系列
            "奥德赛": "超级马力欧 奥德赛",
            "马车8": "马力欧卡丁车8 豪华版",
            "马派": "超级马力欧派对",
            "惊奇": "超级马力欧兄弟 惊奇",
            "马造2": "超级马力欧创作家2",

            # 宝可梦系列
            "朱紫": "宝可梦 朱/紫",
            "剑盾": "宝可梦 剑/盾",
            "阿尔宙斯": "宝可梦传说 阿尔宙斯",
            "珍钻": "宝可梦 晶灿钻石/明亮珍珠",

            # 其他热门
            "动森": "集合啦！动物森友会",
            "喷3": "斯普拉遁3",
            "喷2": "斯普拉遁2",
            "大乱斗": "任天堂明星大乱斗 特别版",
            "奶刃2": "异度神剑2",
            "奶刃3": "异度神剑3",
            "xb2": "异度神剑2",
            "xb3": "异度神剑3",
            "皮克敏4": "皮克敏4",
            "火纹": "火焰纹章",
            "风花雪月": "火焰纹章：风花雪月",
            "engage": "火焰纹章 Engage",
            "逆转": "逆转裁判",
            "mhr": "怪物猎人 崛起",
            "mhrs": "怪物猎人 崛起：曙光",
            "怪猎崛起": "怪物猎人 崛起",
            "p5r": "女神异闻录5 皇家版",
            "p5s": "女神异闻录5 乱战：魅影攻手",
            "异度1": "异度神剑 终极版",
            "猎天使魔女3": "蓓优妮塔3",
            "贝姐3": "蓓优妮塔3",
            "魔女3": "蓓优妮塔3",
            "密特罗德": "密特罗德 生存恐惧",
            "生存恐惧": "密特罗德 生存恐惧",
            "卡比": "星之卡比",
            "探索发现": "星之卡比 探索发现",
            "splt": "斯普拉遁",
        }
        for alias, standard in builtins.items():
            self.add_alias(alias, standard)

    def add_alias(self, alias: str, standard_name: str):
        """添加别名映射。"""
        key = alias.strip().lower()
        self._aliases[key] = standard_name
        self._known_games.add(standard_name)

    def resolve(self, query: str) -> str | None:
        """如果 query 是已知别名，返回标准名称；否则返回 None。"""
        return self._aliases.get(query.strip().lower())

    def learn(self, game_name: str):
        """从搜索结果中学习游戏名。"""
        self._known_games.add(game_name.strip())

    def search_hints(self, query: str, limit: int = 10) -> list[str]:
        """返回可能与 query 匹配的已知游戏名。"""
        q = query.strip().lower()
        if not q:
            return []

        results: list[tuple[str, float]] = []

        # 精确别名匹配
        alias = self._aliases.get(q)
        if alias:
            results.append((alias, 0.0))

        # 包含匹配
        for name in self._known_games:
            name_lower = name.lower()
            if q in name_lower:
                # 相似度：越短匹配越优先
                score = len(q) / max(len(name_lower), 1)
                results.append((name, score))

        results.sort(key=lambda x: x[1])
        return [name for name, _ in results[:limit]]
