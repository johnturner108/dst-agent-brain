#!/usr/bin/env python3
"""
DST Agent Brain - Main Entry Point
A sophisticated AI agent for Don't Starve Together game automation
"""

import uvicorn
import logging
import os
import sys
import argparse
from src.api.server import app
from src.config.settings import settings

# 全局变量存储当前使用的配置名称
CURRENT_CONFIG_NAME = None

# 确保所有必要的目录存在
settings.ensure_directories()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(settings.LOGS_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the DST Agent Brain application"""
    global CURRENT_CONFIG_NAME
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="DST Agent Brain Server")
    parser.add_argument("--config", "-c", type=str, help="配置名称")
    args = parser.parse_args()
    
    logger.info("Starting DST Agent Brain server...")
    
    try:
        # 验证配置是否存在
        if args.config:
            logger.info(f"使用配置: {args.config}")
            try:
                settings.get_ai_config(args.config)
                settings.set_current_config(args.config)
                CURRENT_CONFIG_NAME = args.config
            except ValueError as e:
                logger.error(f"配置错误: {e}")
                sys.exit(1)
        else:
            logger.info("使用默认配置")
            CURRENT_CONFIG_NAME = None
        
        server_config = settings.get_server_config()
        uvicorn.run(
            "src.api.server:app",
            host=server_config["host"],
            port=server_config["port"],
            reload=server_config["reload"],
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main() 