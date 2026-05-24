"""解析游戏详情页的 url 字段，提取网盘链接、版本、金手指信息。

url 字段格式示例:
    [百度网盘]：https://pan.baidu.com/s/xxx?pwd=thwj
    [夸克网盘]：https://pan.quark.cn/s/xxx
    最新版本：1.6.0
    含1.1.2金手指
"""

import re
import logging
from .models import CloudDiskLink, DiskType

logger = logging.getLogger(__name__)

# 网盘标签正则
DISK_PATTERNS = {
    DiskType.BAIDU: re.compile(r"\[百度网盘\]\s*[：:]\s*(https?://pan\.baidu\.com/[^\s]+)"),
    DiskType.QUARK: re.compile(r"\[夸克网盘\]\s*[：:]\s*(https?://pan\.quark\.cn/[^\s]+)"),
    DiskType.ALIYUN: re.compile(r"\[阿里云盘\]\s*[：:]\s*(https?://[^\s]+)"),
}

# 百度网盘提取码
PWD_PATTERN = re.compile(r"[?&]pwd=([A-Za-z0-9]+)")

# 版本号
VERSION_PATTERN = re.compile(r"最新版本[：:]\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)")

# 金手指
CHEAT_PATTERN = re.compile(r"含\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)\s*金手指")


def parse_game_url(url_text: str) -> tuple[list[CloudDiskLink], str | None, bool]:
    """从游戏 url 字段中解析网盘链接、版本号、金手指标志。

    Args:
        url_text: 原始 url 字段内容

    Returns:
        (links, version, has_cheats)
    """
    links: list[CloudDiskLink] = []

    for disk_type, pattern in DISK_PATTERNS.items():
        for match in pattern.finditer(url_text):
            link_url = match.group(1).strip()
            password = None

            if disk_type == DiskType.BAIDU:
                pwd_match = PWD_PATTERN.search(link_url)
                if pwd_match:
                    password = pwd_match.group(1)

            links.append(CloudDiskLink(
                disk_type=disk_type,
                url=link_url,
                password=password,
            ))

    # 版本号
    version = None
    ver_match = VERSION_PATTERN.search(url_text)
    if ver_match:
        version = ver_match.group(1)

    # 金手指
    has_cheats = bool(CHEAT_PATTERN.search(url_text))

    return links, version, has_cheats
