import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FileManagerService:
    """Service for file management operations"""
    
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
