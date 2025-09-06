"""
Tests for configuration module
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from anajobs.config import get_config, create_default_config, DEFAULT_CONFIG


class TestConfig:
    """Test cases for configuration management"""
    
    def test_get_config_defaults(self):
        """Test getting default configuration"""
        with patch('anajobs.config.Path.exists', return_value=False):
            config = get_config()
            
            assert config == DEFAULT_CONFIG
            assert config["mongodb_uri"] == "mongodb://localhost:27017/"
            assert config["database_name"] == "nonprofit_jobs"
            assert config["collection_name"] == "organizations"
    
    def test_get_config_from_file(self):
        """Test loading configuration from file"""
        test_config = {
            "mongodb_uri": "mongodb://test:27017/",
            "database_name": "test_db",
            "log_level": "DEBUG"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_file_path = f.name
        
        try:
            with patch('anajobs.config.Path.exists', return_value=True):
                with patch('anajobs.config.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
                    
                    config = get_config()
                    
                    # Should have default values updated with file values
                    assert config["mongodb_uri"] == "mongodb://test:27017/"
                    assert config["database_name"] == "test_db"
                    assert config["log_level"] == "DEBUG"
                    # Defaults should still be present
                    assert config["collection_name"] == "organizations"
        finally:
            os.unlink(temp_file_path)
    
    @patch.dict(os.environ, {
        'ANAJOBS_MONGODB_URI': 'mongodb://env:27017/',
        'ANAJOBS_DATABASE_NAME': 'env_database',
        'ANAJOBS_LOG_LEVEL': 'WARNING'
    })
    def test_get_config_from_env(self):
        """Test loading configuration from environment variables"""
        with patch('anajobs.config.Path.exists', return_value=False):
            config = get_config()
            
            assert config["mongodb_uri"] == "mongodb://env:27017/"
            assert config["database_name"] == "env_database"
            assert config["log_level"] == "WARNING"
            # Defaults should still be present for non-overridden values
            assert config["collection_name"] == "organizations"
    
    @patch.dict(os.environ, {
        'ANAJOBS_MONGODB_URI': 'mongodb://env:27017/',
        'ANAJOBS_LOG_LEVEL': 'ERROR'
    })
    def test_get_config_precedence(self):
        """Test configuration precedence (env > file > defaults)"""
        file_config = {
            "mongodb_uri": "mongodb://file:27017/",
            "database_name": "file_database",
            "log_level": "DEBUG"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(file_config, f)
            temp_file_path = f.name
        
        try:
            with patch('anajobs.config.Path.exists', return_value=True):
                with patch('anajobs.config.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(file_config)
                    
                    config = get_config()
                    
                    # Environment should override file
                    assert config["mongodb_uri"] == "mongodb://env:27017/"
                    assert config["log_level"] == "ERROR"
                    # File should override defaults
                    assert config["database_name"] == "file_database"
                    # Defaults should be present for non-overridden values
                    assert config["collection_name"] == "organizations"
        finally:
            os.unlink(temp_file_path)
    
    def test_get_config_invalid_json(self):
        """Test handling invalid JSON in config file"""
        with patch('anajobs.config.Path.exists', return_value=True):
            with patch('anajobs.config.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"
                
                # Should fall back to defaults when JSON is invalid
                config = get_config()
                assert config == DEFAULT_CONFIG
    
    @patch('anajobs.config.Path.mkdir')
    @patch('anajobs.config.Path.exists')
    def test_create_default_config_new(self, mock_exists, mock_mkdir):
        """Test creating default config file when it doesn't exist"""
        mock_exists.return_value = False
        
        with patch('anajobs.config.open', create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
            
            create_default_config()
            
            mock_mkdir.assert_called_once_with(exist_ok=True)
            mock_open.assert_called_once()
            mock_file.write.assert_called_once()
    
    @patch('anajobs.config.Path.exists')
    def test_create_default_config_exists(self, mock_exists):
        """Test creating default config file when it already exists"""
        mock_exists.return_value = True
        
        with patch('anajobs.config.open', create=True) as mock_open:
            create_default_config()
            
            # Should not try to write file if it already exists
            mock_open.assert_not_called()


class TestConfigIntegration:
    """Integration tests for configuration"""
    
    def test_default_config_values(self):
        """Test that default config values are reasonable"""
        config = DEFAULT_CONFIG
        
        assert "mongodb://" in config["mongodb_uri"]
        assert config["database_name"]
        assert config["collection_name"]
        assert config["log_level"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert config["data_file"]
        assert config["log_file"]
    
    def test_all_env_vars_mapped(self):
        """Test that all environment variables have corresponding config keys"""
        from anajobs.config import get_config
        
        env_vars = [
            "ANAJOBS_MONGODB_URI",
            "ANAJOBS_DATABASE_NAME", 
            "ANAJOBS_COLLECTION_NAME",
            "ANAJOBS_DATA_FILE",
            "ANAJOBS_LOG_LEVEL",
            "ANAJOBS_LOG_FILE"
        ]
        
        # Set all env vars
        env_dict = {var: f"test_{var.lower()}" for var in env_vars}
        
        with patch.dict(os.environ, env_dict):
            with patch('anajobs.config.Path.exists', return_value=False):
                config = get_config()
                
                # All env vars should be reflected in config
                assert config["mongodb_uri"] == "test_anajobs_mongodb_uri"
                assert config["database_name"] == "test_anajobs_database_name"
                assert config["collection_name"] == "test_anajobs_collection_name"
                assert config["data_file"] == "test_anajobs_data_file"
                assert config["log_level"] == "test_anajobs_log_level"
                assert config["log_file"] == "test_anajobs_log_file"


if __name__ == "__main__":
    pytest.main([__file__])