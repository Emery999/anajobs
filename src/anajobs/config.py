"""
Configuration management for AnaJobs
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "mongodb_uri": "mongodb://localhost:27017/",
    "database_name": "nonprofit_jobs",
    "collection_name": "organizations",
    "data_file": "data/publicserviceopenings.jsonl",
    "log_level": "INFO",
    "log_file": "logs/anajobs.log"
}

def get_config() -> Dict[str, Any]:
    """
    Load configuration from multiple sources in order of precedence:
    1. Environment variables
    2. config/config.json file
    3. Default values
    """
    config = DEFAULT_CONFIG.copy()
    
    # Load from config file if it exists
    config_file = Path("config/config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    # Override with environment variables
    env_mapping = {
        "ANAJOBS_MONGODB_URI": "mongodb_uri",
        "ANAJOBS_DATABASE_NAME": "database_name",
        "ANAJOBS_COLLECTION_NAME": "collection_name",
        "ANAJOBS_DATA_FILE": "data_file",
        "ANAJOBS_LOG_LEVEL": "log_level",
        "ANAJOBS_LOG_FILE": "log_file"
    }
    
    for env_var, config_key in env_mapping.items():
        value = os.getenv(env_var)
        if value:
            config[config_key] = value
    
    return config

def create_default_config():
    """Create a default config.json file"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "config.json"
    
    if not config_file.exists():
        with open(config_file, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        
        print(f"Created default configuration file: {config_file}")
    else:
        print(f"Configuration file already exists: {config_file}")

if __name__ == "__main__":
    create_default_config()