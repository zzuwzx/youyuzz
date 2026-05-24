"""Tests for scraper module."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.parser import parse_game_url
from scraper.models import DiskType, CloudDiskLink
from scraper.game_dict import GameNameDict


class TestParser:
    def test_parse_single_quark(self):
        links, version, cheats = parse_game_url(
            "[夸克网盘]：https://pan.quark.cn/s/abc123"
        )
        assert len(links) == 1
        assert links[0].disk_type == DiskType.QUARK
        assert links[0].url == "https://pan.quark.cn/s/abc123"
        assert version is None
        assert cheats is False

    def test_parse_baidu_with_password(self):
        links, version, cheats = parse_game_url(
            "[百度网盘]：https://pan.baidu.com/s/1Psd9qVDE0DgPkWmdGw-vTQ?pwd=thwj"
        )
        assert len(links) == 1
        assert links[0].disk_type == DiskType.BAIDU
        assert links[0].password == "thwj"

    def test_parse_multiple_disks(self):
        text = (
            "[百度网盘]：https://pan.baidu.com/s/xxx?pwd=abc\n"
            "[夸克网盘]：https://pan.quark.cn/s/yyy\n"
        )
        links, version, cheats = parse_game_url(text)
        assert len(links) == 2
        types = {l.disk_type for l in links}
        assert DiskType.BAIDU in types
        assert DiskType.QUARK in types

    def test_parse_version(self):
        links, version, cheats = parse_game_url(
            "[夸克网盘]：https://pan.quark.cn/s/xxx\n最新版本：1.6.0"
        )
        assert version == "1.6.0"

    def test_parse_version_multidigit(self):
        links, version, cheats = parse_game_url(
            "[夸克网盘]：https://pan.quark.cn/s/xxx\n最新版本：2.34.567"
        )
        assert version == "2.34.567"

    def test_parse_cheats(self):
        links, version, cheats = parse_game_url(
            "[夸克网盘]：https://pan.quark.cn/s/xxx\n含1.1.2金手指"
        )
        assert cheats is True

    def test_parse_empty(self):
        links, version, cheats = parse_game_url("")
        assert links == []
        assert version is None
        assert cheats is False

    def test_parse_real_world_sample(self):
        text = (
            "[百度网盘]：https://pan.baidu.com/s/1Psd9qVDE0DgPkWmdGw-vTQ?pwd=thwj\n"
            "[夸克网盘]：https://pan.quark.cn/s/231eef83dbaf\n"
            "最新版本：1.6.0\n"
            "含1.1.2金手指"
        )
        links, version, cheats = parse_game_url(text)
        assert len(links) == 2
        assert version == "1.6.0"
        assert cheats is True


class TestGameNameDict:
    def test_exact_alias(self):
        gd = GameNameDict()
        result = gd.resolve("野炊")
        assert result == "塞尔达传说：旷野之息"

    def test_case_insensitive(self):
        gd = GameNameDict()
        result = gd.resolve("BOTW")
        assert result == "塞尔达传说：旷野之息"

    def test_add_custom_alias(self):
        gd = GameNameDict()
        gd.add_alias("测试", "测试游戏")
        assert gd.resolve("测试") == "测试游戏"

    def test_resolve_unknown(self):
        gd = GameNameDict()
        assert gd.resolve("不存在的游戏") is None

    def test_search_hints(self):
        gd = GameNameDict()
        gd.learn("塞尔达传说：王国之泪")
        gd.learn("塞尔达传说：旷野之息")
        hints = gd.search_hints("塞尔达")
        assert len(hints) >= 2

    def test_learn_from_search(self):
        gd = GameNameDict()
        gd.learn("新游戏 中文版")
        assert "新游戏 中文版" in gd._known_games
