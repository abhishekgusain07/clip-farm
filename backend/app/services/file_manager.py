
import os
import asyncio
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class FileManagerService:
    """Service for file management operations"""
    
    @staticmethod
    async def cleanup_file(file_path: str) -> bool:
        """Clean up a single file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    async def cleanup_files(file_paths: List[str]) -> int:
        """Clean up multiple files"""
        cleaned_count = 0
        for file_path in file_paths:
            if await FileManagerService.cleanup_file(file_path):
                cleaned_count += 1
        return cleaned_count
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    @staticmethod
    def ensure_directory(directory: str) -> Path:
        """Ensure directory exists"""
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return path
