#!/usr/bin/env python3
"""
DST Agent Brain - Main Entry Point
A sophisticated AI agent for Don't Starve Together game automation
"""

import uvicorn
import logging
import os
from src.api.server import app
from src.config.settings import settings

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
    logger.info("Starting DST Agent Brain server...")
    
    try:
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