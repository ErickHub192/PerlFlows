# app/routers/frontend_logs_router.py - Frontend logs collection endpoint

import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Request
from pydantic import BaseModel

# Setup frontend logger
frontend_logger = logging.getLogger('frontend')
frontend_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

# Setup file handler for frontend logs
frontend_log_file = os.path.join(logs_dir, 'frontend.log')
frontend_handler = logging.FileHandler(frontend_log_file, encoding='utf-8')
frontend_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - FRONTEND - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
frontend_handler.setFormatter(formatter)
frontend_logger.addHandler(frontend_handler)

router = APIRouter(prefix="/api", tags=["frontend-logs"])

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    url: str
    userAgent: str

class FrontendLogsRequest(BaseModel):
    logs: List[LogEntry]
    source: str

@router.post("/frontend-logs")
async def receive_frontend_logs(request: FrontendLogsRequest):
    """
    Receive frontend logs and save them to backend log files
    """
    try:
        for log_entry in request.logs:
            # Format log message with frontend context
            log_message = f"[{log_entry.url}] {log_entry.message}"
            
            # Map frontend log levels to Python logging levels
            level_mapping = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARN': logging.WARNING,
                'ERROR': logging.ERROR
            }
            
            log_level = level_mapping.get(log_entry.level, logging.INFO)
            
            # Log to frontend logger
            frontend_logger.log(log_level, log_message)
        
        return {
            "success": True,
            "message": f"Received {len(request.logs)} frontend log entries",
            "processed": len(request.logs)
        }
        
    except Exception as e:
        frontend_logger.error(f"Error processing frontend logs: {str(e)}")
        return {
            "success": False,
            "message": f"Error processing logs: {str(e)}"
        }