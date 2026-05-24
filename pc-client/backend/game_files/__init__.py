"""
game_files: Switch 游戏文件智能识别模块。

从本地目录扫描 .nsp/.nsz/.xci 文件，
自动分类为本体/更新/DLC/金手指，
按安装顺序排列输出。
"""

from .models import GameFile, CheatFile, ScanResult
from .classifier import GameClassifier
from .cheat import CheatHandler

__all__ = ["GameClassifier", "CheatHandler", "GameFile", "CheatFile", "ScanResult"]
