"""
Settings configuration for DST Agent Brain
Centralized configuration management
"""

import os
from typing import Optional

class Settings:
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8081
    API_RELOAD: bool = True
    
    # AI Model Configuration
    AI_MODEL: str = "kimi-k2-0711-preview"
    AI_TEMPERATURE: float = 0.6
    AI_API_KEY: str = "sk-L7Q2cBME4D7Oip201OQicXPrrcbNXP2Rufq4sVtYZtFQlbEb"
    AI_BASE_URL: str = "https://api.moonshot.cn/v1"
    
    # Alternative AI Configuration (commented out)
    # AI_API_KEY: str = "sk-e5c6153187014493bb4802a8aac1b375"
    # AI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # Queue Configuration
    ACTION_QUEUE_SIZE: int = 20
    ACTION_ALLOWED_NUM: int = 1
    DIALOG_QUEUE_SIZE: int = 20
    
    
    # File Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    RECIPE_LIST_FILE_PATH: str = os.path.join(BASE_DIR, "src", "data", "recipes", "recipes_merged_processed.json")
    LOGS_DIR: str = os.path.join(BASE_DIR, "src", "logs")
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
    def get_ai_config(cls) -> dict:
        """Get AI configuration dictionary"""
        return {
            "api_key": cls.AI_API_KEY,
            "base_url": cls.AI_BASE_URL,
            "model": cls.AI_MODEL,
            "temperature": cls.AI_TEMPERATURE
        }
    
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