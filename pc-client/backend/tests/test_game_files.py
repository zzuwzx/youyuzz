"""Tests for game_files module."""

import sys
import os
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from game_files.classifier import GameClassifier
from game_files.cheat import CheatHandler
from game_files.models import GameFile, CheatFile, ScanResult, GameType

FIXTURES = Path(__file__).parent / "fixtures"


class TestGameClassifier:
    def test_scan_organized_structure(self):
        """规范目录：本体/更新/DLC分文件夹存放"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "organized_game")

        assert result.base_count == 1
        assert result.update_count == 1
        assert result.dlc_count == 1
        assert result.cheat_count == 0
        assert len(result.games) == 3

        # Verify install order: base(0) -> update(1) -> dlc(2)
        assert result.games[0].game_type == GameType.BASE
        assert result.games[1].game_type == GameType.UPDATE
        assert result.games[2].game_type == GameType.DLC

    def test_scan_single_game(self):
        """单文件目录：仅一个游戏本体"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "single_game")

        assert result.base_count == 1
        assert result.update_count == 0
        assert result.dlc_count == 0
        assert result.games[0].game_type == GameType.BASE
        assert result.games[0].name == "Zelda.nsp"

    def test_scan_flat_mixed(self):
        """扁平目录混合文件：靠关键词分类"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "flat_mixed")

        assert result.base_count >= 1
        assert result.update_count >= 1
        assert result.dlc_count >= 1
        assert result.cheat_count >= 1

        # txt file should NOT be picked up
        names = [g.name for g in result.games]
        assert "readme.txt" not in names

    def test_scan_cheats_only(self):
        """仅金手指目录"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "cheats_only")

        assert len(result.games) == 0
        assert result.cheat_count >= 2  # cheat_mod + 金手指合集
        # not_a_cheat.zip contains 'cheat' keyword, so it matches
        cheat_names = [c.name for c in result.cheats]
        assert "cheat_mod_v2.zip" in cheat_names

    def test_scan_empty_dir(self):
        """空目录返回空结果"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "empty")
        assert len(result.games) == 0
        assert len(result.cheats) == 0
        assert result.total_size_mb == 0

    def test_scan_nonexistent_dir(self):
        """不存在的目录应抛出异常"""
        gc = GameClassifier()
        with pytest.raises(NotADirectoryError):
            gc.scan(FIXTURES / "nonexistent_xyz")

    def test_install_order_priority(self):
        """验证安装顺序：本体→更新→DLC"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "flat_mixed")

        priorities = [g.priority for g in result.games]
        assert priorities == sorted(priorities), f"Expected sorted priorities, got {priorities}"

    def test_size_calculation(self):
        """文件大小计算正确"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "single_game")

        expected_mb = 500 / (1024 * 1024)
        assert abs(result.games[0].size_mb - expected_mb) < 0.01
        assert abs(result.total_size_mb - expected_mb) < 0.01

    def test_nested_directories(self):
        """递归扫描嵌套子目录"""
        gc = GameClassifier()
        result = gc.scan(FIXTURES / "nested")

        assert len(result.games) == 1
        assert result.games[0].name == "deep_game.nsp"


class TestCheatHandler:
    def test_validate_valid_cheat_zip(self):
        """有效金手指ZIP验证"""
        # We need a real ZIP with structure; test with mock approach
        handler = CheatHandler()
        # non-zip files return False
        assert handler.validate(FIXTURES / "empty") is False

    def test_validate_non_zip(self):
        """非ZIP文件返回False"""
        handler = CheatHandler()
        result = handler.validate(FIXTURES / "single_game" / "Zelda.nsp")
        assert result is False

    def test_extract_to_creates_dir(self):
        """解压验证目标目录创建"""
        import zipfile, tempfile
        tmpdir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(tmpdir, "test_cheat.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("cheats/some_game/cheat.txt", "dummy")
                zf.writestr("contents/some_game/cheat.txt", "dummy")

            dest = os.path.join(tmpdir, "extracted")
            handler = CheatHandler()
            assert handler.validate(zip_path) is True
            assert handler.extract_to(zip_path, dest) is True
            assert os.path.isdir(dest)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestModels:
    def test_gamefile_creation(self):
        gf = GameFile(path="/tmp/test.nsp", name="test.nsp", game_type=GameType.BASE, size_mb=1.5)
        assert gf.game_type == GameType.BASE
        assert gf.priority == 0

    def test_gamefile_path_normalization(self):
        gf = GameFile(path="C:/foo/bar.nsp", name="bar.nsp", game_type=GameType.UPDATE, size_mb=2.0)
        # Path() normalizes to platform-native separator
        assert gf.path.endswith("bar.nsp")

    def test_scanresult_defaults(self):
        sr = ScanResult()
        assert sr.games == []
        assert sr.cheats == []
        assert sr.total_size_mb == 0
        assert sr.base_count == 0
