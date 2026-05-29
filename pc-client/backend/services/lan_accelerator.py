"""
鱿郁仔仔 — 局域网加速模块
自动检测同网段 NAS，走 SMB 内网地址加速下载。

使用方式:
    from services.lan_accelerator import LanAccelerator
    
    accelerator = LanAccelerator()
    nas_url = accelerator.get_nas_url()  # 返回内网或公网地址
"""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NasConfig:
    """NAS 配置"""
    # 公网地址（默认）
    public_host: str = ""
    # 内网地址
    lan_host: str = ""
    # SMB 端口
    smb_port: int = 445
    # HTTP 端口（用于下载）
    http_port: int = 8080
    # 共享名
    share_name: str = "youyuzz"
    # 用户名
    username: str = ""
    # 密码
    password: str = ""


class LanAccelerator:
    """
    局域网加速器
    检测当前网络环境，自动选择最快的 NAS 地址。
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self._config = NasConfig()
        self._is_lan = False
        self._cached_url: Optional[str] = None
        
        # 加载配置
        if config_path and config_path.exists():
            self._load_config(config_path)
        
        # 检测网络环境
        self._detect_network()
    
    def _load_config(self, path: Path) -> None:
        """从 JSON 文件加载 NAS 配置"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._config = NasConfig(
                public_host=data.get("nas_public_host", ""),
                lan_host=data.get("nas_lan_host", ""),
                smb_port=data.get("nas_smb_port", 445),
                http_port=data.get("nas_http_port", 8080),
                share_name=data.get("nas_share_name", "youyuzz"),
                username=data.get("nas_username", ""),
                password=data.get("nas_password", ""),
            )
            logger.info("已加载 NAS 配置: %s", path)
        except Exception:
            logger.warning("加载 NAS 配置失败", exc_info=True)
    
    def _detect_network(self) -> None:
        """检测当前网络环境"""
        if not self._config.lan_host:
            logger.info("未配置 NAS 内网地址，跳过局域网检测")
            return
        
        try:
            # 获取本机 IP
            local_ip = self._get_local_ip()
            if not local_ip:
                return
            
            # 检查是否与 NAS 在同一网段
            local_net = ipaddress.ip_network(f"{local_ip}/24", strict=False)
            nas_ip = ipaddress.ip_address(self._config.lan_host)
            
            if nas_ip in local_net:
                # 测试 NAS 是否可达
                if self._test_connection(self._config.lan_host, self._config.smb_port):
                    self._is_lan = True
                    logger.info("检测到局域网环境，NAS 可达: %s", self._config.lan_host)
                else:
                    logger.warning("NAS 内网地址不可达: %s", self._config.lan_host)
            else:
                logger.info("不在同一网段，使用公网地址")
                
        except Exception:
            logger.warning("网络检测失败", exc_info=True)
    
    def _get_local_ip(self) -> Optional[str]:
        """获取本机局域网 IP"""
        try:
            # 通过连接外部地址获取本机 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
    
    def _test_connection(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """测试 TCP 连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    @property
    def is_lan(self) -> bool:
        """是否在局域网环境"""
        return self._is_lan
    
    def get_nas_url(self, path: str = "") -> str:
        """
        获取 NAS 访问地址
        
        Args:
            path: 资源路径
        
        Returns:
            完整的 NAS URL
        """
        if self._is_lan and self._config.lan_host:
            base = f"http://{self._config.lan_host}:{self._config.http_port}"
        elif self._config.public_host:
            base = f"http://{self._config.public_host}"
        else:
            return ""
        
        if path:
            return f"{base}/{path.lstrip('/')}"
        return base
    
    def get_smb_url(self) -> str:
        """获取 SMB 连接 URL"""
        if not self._config.lan_host:
            return ""
        return f"smb://{self._config.lan_host}/{self._config.share_name}"
    
    def get_status(self) -> dict:
        """获取加速器状态"""
        return {
            "is_lan": self._is_lan,
            "local_ip": self._get_local_ip(),
            "nas_lan_host": self._config.lan_host,
            "nas_public_host": self._config.public_host,
            "active_url": self.get_nas_url(),
        }


# 全局实例
_accelerator: Optional[LanAccelerator] = None


def get_accelerator() -> LanAccelerator:
    """获取全局加速器实例"""
    global _accelerator
    if _accelerator is None:
        config_path = Path(__file__).parent.parent.parent / "data" / "nas_config.json"
        _accelerator = LanAccelerator(config_path)
    return _accelerator