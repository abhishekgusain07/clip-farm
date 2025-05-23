from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VideoBase(BaseModel):
    """Base schema for video data"""
    video_id: str
    file_path: str
    file_size: Optional[int] = None
    duration: Optional[int] = None

class VideoCreate(VideoBase):
    """Schema for creating video record"""
    pass

class VideoResponse(VideoBase):
    """Schema for video response"""
    downloaded_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
