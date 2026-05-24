"""金手指压缩包处理。

检测、验证、提取 Switch 金手指压缩包。
"""

import zipfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CheatHandler:
    """金手指处理器。

    用法:
        handler = CheatHandler()
        valid = handler.validate("/path/to/cheats.zip")
        if valid:
            handler.extract_to("/path/to/sd/atmosphere/contents/")
    """

    # 金手指包应有的典型内容
    EXPECTED_CONTENTS = {"cheats", "contents", "atmosphere"}

    @staticmethod
    def validate(cheat_path: str | Path) -> bool:
        """验证 ZIP 是否为有效金手指包。

        Args:
            cheat_path: ZIP 文件路径

        Returns:
            True 如果包结构合法
        """
        path = Path(cheat_path)
        if not path.suffix.lower() == ".zip":
            return False
        if not path.is_file():
            return False

        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = [n.lower() for n in zf.namelist()]
                # 检查是否包含典型金手指目录结构
                has_structure = any(
                    "cheats" in n or "contents" in n for n in names
                )
                return has_structure
        except (zipfile.BadZipFile, OSError) as e:
            logger.warning("无效的 ZIP 文件 %s: %s", path.name, e)
            return False

    @staticmethod
    def extract_to(cheat_path: str | Path, dest_dir: str | Path) -> bool:
        """解压金手指到目标目录。

        Args:
            cheat_path: ZIP 文件路径
            dest_dir: 解压目标目录（通常为 SD 卡 atmosphere/contents/）

        Returns:
            True 如果解压成功
        """
        src = Path(cheat_path)
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(dest)
            logger.info("金手指解压成功: %s -> %s", src.name, dest)
            return True
        except (zipfile.BadZipFile, OSError) as e:
            logger.error("金手指解压失败 %s: %s", src.name, e)
            return False
