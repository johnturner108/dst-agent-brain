"""
Settings configuration for DST Agent Brain
Centralized configuration management
"""

import os
import json
from typing import Optional, Dict, Any

class Settings:
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8081
    API_RELOAD: bool = True
    
    # AI Model Configuration - 从config.json读取
    _config_cache: Optional[Dict[str, Any]] = None
    
    # Queue Configuration
    ACTION_QUEUE_SIZE: int = 20
    ACTION_ALLOWED_NUM: int = 1
    DIALOG_QUEUE_SIZE: int = 20
    
    
    # File Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    RECIPE_LIST_FILE_PATH: str = os.path.join(BASE_DIR, "recipes", "recipes_merged_processed.json")
    LOGS_DIR: str = os.path.join(BASE_DIR, "logs")
    CHAT_LOG_DIR: str = os.path.join(LOGS_DIR, "chat_log")
    # 暂时保持 memory 目录在根目录，直到用户决定移动它
    MEMORY_DIR: str = os.path.join(BASE_DIR, "memory")
    MAP_FILE_PATH: str = os.path.join(MEMORY_DIR, "map.json")
    
    # Observer Configuration
    OBSERVER_CLEANUP_INTERVAL: int = 120  # seconds
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        """从config.json加载配置"""
        if cls._config_cache is not None:
            return cls._config_cache
        
        config_path = os.path.join(cls.BASE_DIR, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cls._config_cache = json.load(f)
                return cls._config_cache
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    @classmethod
    def get_ai_config(cls) -> dict:
        """从config.json获取AI配置"""
        config = cls._load_config()
        return {
            "api_key": config["api_key"],
            "base_url": config["base_url"],
            "model": config["model_name"],  # config.json中是model_name
            "temperature": config["temperature"]
        }
    
    @classmethod
    def get_ai_model_type(cls) -> str:
        """获取AI模型类型，默认为openai_compatible"""
        return "openai_compatible"
    
    @classmethod
    def get_server_config(cls) -> dict:
        """Get server configuration dictionary"""
        return {
            "host": cls.API_HOST,
            "port": cls.API_PORT,
            "reload": cls.API_RELOAD
        }
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.LOGS_DIR,
            cls.CHAT_LOG_DIR,
            cls.MEMORY_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

# Global settings instance
settings = Settings() 