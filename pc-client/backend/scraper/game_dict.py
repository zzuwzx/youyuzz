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
            "spl2": "斯普拉遁2",
            "spl3": "斯普拉遁3",
            "鬼屋3": "路易吉洋馆3",
            "lm3": "路易吉洋馆3",
            "纸马": "纸片马力欧：折纸国王",
            "3D世界": "超级马力欧3D世界 + 狂怒世界",
            "马RPG": "超级马力欧RPG",
            "马网": "马力欧网球 王牌",
            "马高": "马力欧高尔夫 超级冲冲冲",
            "耀西": "耀西的手工世界",
            "大金刚": "森喜刚 热带冻结",
            "热带冻结": "森喜刚 热带冻结",
            "pikmin4": "皮克敏4",
            "卡比同盟": "星之卡比 新星同盟",
            "卡比重返": "星之卡比 重返梦幻岛 豪华版",
            "mp重制": "密特罗德 Prime 重制版",
            "火纹无双": "火焰纹章无双 风花雪月",
            "健身环": "健身环大冒险",
            "51大全": "世界游戏大全51",
            "ns运动": "Nintendo Switch 运动",
            "12switch": "1-2-Switch",
            "arms": "ARMS",
            "瓦力欧": "瓦力欧制造 分享同乐！",
            "马vs咚": "马力欧 vs 咚奇刚",
            "灾厄启示录": "塞尔达无双 灾厄启示录",
            "aoc": "塞尔达无双 灾厄启示录",
            "p4g": "女神异闻录4 黄金版",
            "真女5": "真女神转生5",
            "smt5": "真女神转生5",
            "dq11s": "勇者斗恶龙11S",
            "dq11": "勇者斗恶龙11S",
            "八方旅人": "歧路旅人",
            "octopath": "歧路旅人",
            "八方旅人2": "歧路旅人2",
            "歧路2": "歧路旅人2",
            "三角战略": "三角战略",
            "livealive": "时空勇士",
            "圣兽": "圣兽之王",
            "十三机兵": "十三机兵防卫圈",
            "莱莎1": "莱莎的炼金工房",
            "莱莎2": "莱莎的炼金工房2",
            "莱莎3": "莱莎的炼金工房3",
            "nier": "尼尔 自动人形",
            "bd2": "勇气默示录2",
            "勇气2": "勇气默示录2",
            "witcher3": "巫师3：狂猎",
            "d3": "暗黑破坏神3",
            "暗黑3": "暗黑破坏神3",
            "d2": "暗黑破坏神2：狱火重生",
            "暗黑2": "暗黑破坏神2：狱火重生",
            "老滚5": "上古卷轴5：天际",
            "skyrim": "上古卷轴5：天际",
            "龙信": "龙之信条 黑暗觉者",
            "hk": "空洞骑士",
            "hades": "哈迪斯",
            "星露谷": "星露谷物语",
            "stardew": "星露谷物语",
            "celeste": "蔚蓝",
            "cuphead": "茶杯头",
            "双人": "双人成行",
            "分手厨房": "胡闹厨房2",
            "overcooked2": "胡闹厨房2",
            "isaac": "以撒的结合：重生",
            "dead cells": "死亡细胞",
            "sts": "杀戮尖塔",
            "尖塔": "杀戮尖塔",
            "undertale": "传说之下",
            "ori": "奥日与黑暗森林",
            "ori2": "奥日与萤火意志",
            "terraria": "泰拉瑞亚",
            "太鼓": "太鼓达人",
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
