"""
Tests for auto_updater module
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.auto_updater import AutoUpdater, UpdateInfo


@pytest.fixture
def updater():
    return AutoUpdater(current_version="1.0.0")


class TestAutoUpdater:
    def test_init(self, updater):
        assert updater.current_version == "1.0.0"
    
    def test_is_newer_true(self, updater):
        assert updater._is_newer("1.0.1", "1.0.0") is True
        assert updater._is_newer("1.1.0", "1.0.0") is True
        assert updater._is_newer("2.0.0", "1.0.0") is True
    
    def test_is_newer_false(self, updater):
        assert updater._is_newer("1.0.0", "1.0.0") is False
        assert updater._is_newer("0.9.0", "1.0.0") is False
    
    def test_is_newer_equal(self, updater):
        assert updater._is_newer("1.0.0", "1.0.0") is False
    
    @pytest.mark.asyncio
    async def test_check_update_no_update(self, updater):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.0.0",
            "body": "No changes",
            "assets": []
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            has_update, info = await updater.check_update()
            
            assert has_update is False
            assert info is None
    
    @pytest.mark.asyncio
    async def test_check_update_with_update(self, updater):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.1.0",
            "body": "New features",
            "assets": [
                {
                    "name": "鱿郁仔仔 Setup 1.1.0.exe",
                    "browser_download_url": "https://github.com/test/download/v1.1.0/setup.exe",
                    "size": 1024000
                },
                {
                    "name": "checksums.sha256",
                    "browser_download_url": "https://github.com/test/download/v1.1.0/checksums.sha256",
                    "size": 100
                }
            ]
        }
        
        mock_sha_response = MagicMock()
        mock_sha_response.status_code = 200
        mock_sha_response.text = "abc123def456  setup.exe"
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_response, mock_sha_response]
            has_update, info = await updater.check_update()
            
            assert has_update is True
            assert info is not None
            assert info.version == "1.1.0"
            assert info.download_url == "https://github.com/test/download/v1.1.0/setup.exe"
            assert info.sha256 == "abc123def456"
    
    @pytest.mark.asyncio
    async def test_check_update_api_error(self, updater):
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            has_update, info = await updater.check_update()
            
            assert has_update is False
            assert info is None
    
    @pytest.mark.asyncio
    async def test_check_update_network_error(self, updater):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")
            has_update, info = await updater.check_update()
            
            assert has_update is False
            assert info is None
    
    def test_verify_sha256(self, updater, tmp_path):
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Calculate expected hash
        import hashlib
        expected_hash = hashlib.sha256(b"Hello, World!").hexdigest()
        
        assert updater._verify_sha256(test_file, expected_hash) is True
        assert updater._verify_sha256(test_file, "wrong_hash") is False