"""游戏文件智能分类器。

从 SquidInstallerGUI.py 的 SmartScanner 移植并增强：
- 递归扫描 .nsp/.nsz/.xci 文件
- 通过文件/父目录关键词分类：本体/更新/DLC
- 检测 .zip 金手指压缩包
- 按安装顺序（本体→更新→DLC→金手指）排列
"""

import logging
from pathlib import Path
from typing import Optional

from .models import GameFile, CheatFile, ScanResult, GameType

logger = logging.getLogger(__name__)

# -- 关键词匹配规则 --
# 优先级：文件名匹配 > 父目录名匹配
BASE_KEYWORDS = [
    "base", "本体", "v0", "v1.0", "[v0]", "[v1.",
]

UPDATE_KEYWORDS = [
    "upd", "update", "更新", "升级", "补丁",
    "v1.", "v2.", "v3.", "v4.", "v5.",
    "v65536", "v131072", "v196608", "v262144",
]

DLC_KEYWORDS = [
    "dlc", "追加", "扩展", "addon",
    "additional content", "expansion",
]

CHEAT_KEYWORDS = [
    "金手指", "cheat", "cht", "mod",
    "修改", "作弊",
]

# 游戏文件后缀
GAME_EXTENSIONS = frozenset({".nsp", ".nsz", ".xci"})


class GameClassifier:
    """游戏文件分类器。

    用法:
        classifier = GameClassifier()
        result = classifier.scan("/path/to/games/")
        for game in result.games:
            print(f"{game.game_type}: {game.name} ({game.size_mb:.1f}MB)")
    """

    def scan(self, folder_path: str | Path) -> ScanResult:
        """扫描目录，分类所有游戏文件。

        Args:
            folder_path: 游戏资源目录路径

        Returns:
            ScanResult: 包含已排序的游戏文件和金手指列表
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            raise NotADirectoryError(f"路径不存在或不是目录: {folder_path}")

        games: list[GameFile] = []
        cheats: list[CheatFile] = []

        try:
            for entry in folder.rglob("*"):
                if not entry.is_file():
                    continue

                suffix = entry.suffix.lower()

                if suffix in GAME_EXTENSIONS:
                    game_file = self._classify_game(entry)
                    if game_file:
                        games.append(game_file)

                elif suffix == ".zip":
                    cheat_file = self._detect_cheat(entry)
                    if cheat_file:
                        cheats.append(cheat_file)

        except PermissionError as e:
            logger.warning("目录权限不足，跳过部分文件: %s", e)
        except OSError as e:
            logger.error("扫描目录出错: %s", e)
            raise

        # 按安装顺序排列：本体(0) → 更新(1) → DLC(2)
        games.sort(key=lambda g: (g.priority, g.name))

        # 汇总统计
        result = ScanResult(
            games=games,
            cheats=cheats,
            total_size_mb=sum(g.size_mb for g in games),
            base_count=sum(1 for g in games if g.game_type == GameType.BASE),
            update_count=sum(1 for g in games if g.game_type == GameType.UPDATE),
            dlc_count=sum(1 for g in games if g.game_type == GameType.DLC),
            cheat_count=len(cheats),
        )

        logger.info(
            "扫描完成: %s — %d本体/%d更新/%dDLC/%d金手指, 总计%.1fMB",
            folder.name,
            result.base_count,
            result.update_count,
            result.dlc_count,
            result.cheat_count,
            result.total_size_mb,
        )
        return result

    def _classify_game(self, filepath: Path) -> Optional[GameFile]:
        """分类单个游戏文件。"""
        name_lower = filepath.name.lower()
        parent_lower = filepath.parent.name.lower()
        combined = f"{parent_lower} {name_lower}"

        # 优先检测更新（因为更新文件名常含版本号，容易和本体混淆）
        if self._match_any(combined, UPDATE_KEYWORDS):
            game_type = GameType.UPDATE
            priority = 1
        elif self._match_any(combined, DLC_KEYWORDS):
            game_type = GameType.DLC
            priority = 2
        elif self._match_any(combined, BASE_KEYWORDS):
            game_type = GameType.BASE
            priority = 0
        else:
            # 无明确关键词 → 默认本体
            game_type = GameType.BASE
            priority = 0

        try:
            size_bytes = filepath.stat().st_size
        except OSError:
            return None

        return GameFile(
            path=str(filepath),
            name=filepath.name,
            game_type=game_type,
            priority=priority,
            size_mb=size_bytes / (1024 * 1024),
        )

    def _detect_cheat(self, filepath: Path) -> Optional[CheatFile]:
        """检测是否为金手指压缩包。"""
        name_lower = filepath.name.lower()
        parent_lower = filepath.parent.name.lower()
        combined = f"{parent_lower} {name_lower}"

        if self._match_any(combined, CHEAT_KEYWORDS):
            return CheatFile(path=str(filepath), name=filepath.name)
        return None

    @staticmethod
    def _match_any(text: str, keywords: list[str]) -> bool:
        """任一关键词匹配。"""
        return any(k in text for k in keywords)
