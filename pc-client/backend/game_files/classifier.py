"""游戏文件智能分类器。

从 SquidInstallerGUI.py 的 SmartScanner 移植并增强：
- 递归扫描 .nsp/.nsz/.xci/.xcz 文件
- 通过文件/父目录关键词分类：本体/更新/DLC
- 检测 .zip 金手指压缩包
- 按安装顺序（本体→更新→DLC→金手指）排列
- 正则版本号检测，精确区分 v1.0（本体）与 v1.0.1（更新）
- 多语言关键词支持：中/英/韩/西/德/法/意/葡/俄
"""

import logging
import re
from pathlib import Path
from typing import Optional

from .models import GameFile, CheatFile, ScanResult, GameType

logger = logging.getLogger(__name__)

# -- 关键词匹配规则 --
BASE_KEYWORDS = [
    "base", "本体", "본체",
    "v0", "[v0]",
]

UPDATE_KEYWORDS = [
    # 显式更新标识（多语言）
    "upd", "update", "更新", "升级", "补丁",
    "patch", "패치", "parche",
    "actualizacion", "actualización", "atualização",
    "aktualisierung", "aggiornamento",
    # Switch 标题版本 ID
    "v65536", "v131072", "v196608", "v262144",
    "[v65536]", "[v131072]", "[v196608]", "[v262144]",
]

DLC_KEYWORDS = [
    "dlc", "追加", "拡張", "addon",
    "additional content", "expansion",
    "unlocker", "확장팩",
]

CHEAT_KEYWORDS = [
    "金手指", "cheat", "cht", "mod",
    "修改", "作弊",
    "치트", "트레이너",
    "trucos", "triche", "trainer",
]

GAME_EXTENSIONS = frozenset({".nsp", ".nsz", ".xci", ".xcz"})


class GameClassifier:
    """游戏文件分类器。"""

    def scan(self, folder_path: str | Path) -> ScanResult:
        """扫描目录，分类所有游戏文件。"""
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

        games.sort(key=lambda g: (g.priority, g.name))

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

        if self._match_any(combined, UPDATE_KEYWORDS) or self._is_update_version(combined):
            game_type = GameType.UPDATE
            priority = 1
        elif self._match_any(combined, DLC_KEYWORDS):
            game_type = GameType.DLC
            priority = 2
        elif self._match_any(combined, BASE_KEYWORDS):
            game_type = GameType.BASE
            priority = 0
        else:
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
    def _is_update_version(text: str) -> bool:
        """用正则判断文本中的版本号是否表明是更新文件。

        v65536/v131072/v196608/v262144 → 更新
        vX.Y.Z 且末尾段>0 或中间段>0 → 更新
        vX.Y 且 Y>0 → 更新
        v1.0/v2.0/v1.0.0 → 本体
        """
        if re.search(r"v(?:65536|131072|196608|262144)", text):
            return True
        m = re.search(r"v(\d+)\.(\d+)\.(\d+)", text)
        if m:
            minor, patch = int(m.group(2)), int(m.group(3))
            return patch > 0 or minor > 0
        m = re.search(r"v(\d+)\.(\d+)", text)
        if m and int(m.group(2)) > 0:
            return True
        return False

    @staticmethod
    def _match_any(text: str, keywords: list[str]) -> bool:
        """任一关键词匹配。"""
        return any(k in text for k in keywords)
