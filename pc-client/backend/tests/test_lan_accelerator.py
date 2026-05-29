"""
Tests for lan_accelerator module
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from services.lan_accelerator import LanAccelerator, NasConfig


@pytest.fixture
def nas_config_file(tmp_path):
    """Create a temporary NAS config file"""
    config = {
        "nas_public_host": "nas.example.com",
        "nas_lan_host": "192.168.1.100",
        "nas_smb_port": 445,
        "nas_http_port": 8080,
        "nas_share_name": "youyuzz",
        "nas_username": "test",
        "nas_password": "test"
    }
    config_file = tmp_path / "nas_config.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    return config_file


class TestNasConfig:
    def test_default_values(self):
        config = NasConfig()
        assert config.public_host == ""
        assert config.lan_host == ""
        assert config.smb_port == 445
        assert config.http_port == 8080
        assert config.share_name == "youyuzz"


class TestLanAccelerator:
    def test_init_without_config(self):
        accelerator = LanAccelerator()
        assert accelerator.is_lan is False
    
    def test_init_with_config(self, nas_config_file):
        accelerator = LanAccelerator(config_path=nas_config_file)
        assert accelerator._config.lan_host == "192.168.1.100"
        assert accelerator._config.public_host == "nas.example.com"
    
    def test_load_config(self, nas_config_file):
        accelerator = LanAccelerator()
        accelerator._load_config(nas_config_file)
        assert accelerator._config.lan_host == "192.168.1.100"
    
    def test_load_config_missing_file(self):
        accelerator = LanAccelerator()
        accelerator._load_config(Path("/nonexistent/config.json"))
        # Should not raise exception
        assert accelerator._config.lan_host == ""
    
    @patch("services.lan_accelerator.socket.socket")
    def test_get_local_ip(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ("192.168.1.50", 12345)
        mock_socket_class.return_value = mock_socket
        
        accelerator = LanAccelerator()
        ip = accelerator._get_local_ip()
        assert ip == "192.168.1.50"
    
    @patch("services.lan_accelerator.socket.socket")
    def test_get_local_ip_failure(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception("Network error")
        mock_socket_class.return_value = mock_socket
        
        accelerator = LanAccelerator()
        ip = accelerator._get_local_ip()
        assert ip is None
    
    @patch("services.lan_accelerator.socket.socket")
    def test_test_connection_success(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        accelerator = LanAccelerator()
        result = accelerator._test_connection("192.168.1.100", 445)
        assert result is True
    
    @patch("services.lan_accelerator.socket.socket")
    def test_test_connection_failure(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1
        mock_socket_class.return_value = mock_socket
        
        accelerator = LanAccelerator()
        result = accelerator._test_connection("192.168.1.100", 445)
        assert result is False
    
    def test_get_nas_url_lan(self):
        accelerator = LanAccelerator()
        accelerator._is_lan = True
        accelerator._config.lan_host = "192.168.1.100"
        accelerator._config.http_port = 8080
        
        url = accelerator.get_nas_url()
        assert url == "http://192.168.1.100:8080"
    
    def test_get_nas_url_public(self):
        accelerator = LanAccelerator()
        accelerator._is_lan = False
        accelerator._config.public_host = "nas.example.com"
        
        url = accelerator.get_nas_url()
        assert url == "http://nas.example.com"
    
    def test_get_nas_url_with_path(self):
        accelerator = LanAccelerator()
        accelerator._is_lan = True
        accelerator._config.lan_host = "192.168.1.100"
        accelerator._config.http_port = 8080
        
        url = accelerator.get_nas_url("/games/zelda.nsp")
        assert url == "http://192.168.1.100:8080/games/zelda.nsp"
    
    def test_get_nas_url_no_host(self):
        accelerator = LanAccelerator()
        accelerator._is_lan = False
        accelerator._config.public_host = ""
        
        url = accelerator.get_nas_url()
        assert url == ""
    
    def test_get_smb_url(self):
        accelerator = LanAccelerator()
        accelerator._config.lan_host = "192.168.1.100"
        accelerator._config.share_name = "youyuzz"
        
        url = accelerator.get_smb_url()
        assert url == "smb://192.168.1.100/youyuzz"
    
    def test_get_smb_url_no_host(self):
        accelerator = LanAccelerator()
        accelerator._config.lan_host = ""
        
        url = accelerator.get_smb_url()
        assert url == ""
    
    def test_get_status(self):
        accelerator = LanAccelerator()
        accelerator._is_lan = False
        accelerator._config.lan_host = "192.168.1.100"
        accelerator._config.public_host = "nas.example.com"
        
        status = accelerator.get_status()
        assert "is_lan" in status
        assert "local_ip" in status
        assert "nas_lan_host" in status
        assert "nas_public_host" in status
        assert "active_url" in status
        assert status["nas_lan_host"] == "192.168.1.100"
    
    @patch("services.lan_accelerator.socket.socket")
    def test_detect_network_same_subnet(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ("192.168.1.50", 12345)
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        accelerator = LanAccelerator()
        accelerator._config.lan_host = "192.168.1.100"
        accelerator._detect_network()
        
        assert accelerator.is_lan is True
    
    @patch("services.lan_accelerator.socket.socket")
    def test_detect_network_different_subnet(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ("192.168.2.50", 12345)
        mock_socket_class.return_value = mock_socket
        
        accelerator = LanAccelerator()
        accelerator._config.lan_host = "192.168.1.100"
        accelerator._detect_network()
        
        assert accelerator.is_lan is False
    
    def test_detect_network_no_lan_host(self):
        accelerator = LanAccelerator()
        accelerator._config.lan_host = ""
        accelerator._detect_network()
        
        assert accelerator.is_lan is False