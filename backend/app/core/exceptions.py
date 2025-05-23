from fastapi import HTTPException
from typing import Any, Dict, Optional

class YouTubeClipperException(Exception):
    """Base exception for YouTube Clipper application"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class VideoDownloadException(YouTubeClipperException):
    """Exception raised when video download fails"""
    pass

class VideoProcessingException(YouTubeClipperException):
    """Exception raised when video processing fails"""
    pass

class InvalidURLException(YouTubeClipperException):
    """Exception raised when YouTube URL is invalid"""
    pass

class InvalidTimeFormatException(YouTubeClipperException):
    """Exception raised when time format is invalid"""
    pass

def create_http_exception(status_code: int, message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create HTTP exception with consistent format"""
    return HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "details": details or {}
        }
    )
