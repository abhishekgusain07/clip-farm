from pydantic import BaseModel, Field, validator
import re
from typing import Optional

class ClipRequest(BaseModel):
    """Schema for clip creation request"""
    url: str = Field(..., description="YouTube video URL")
    start_time: str = Field(..., description="Start time in format HH:MM:SS or MM:SS")
    end_time: str = Field(..., description="End time in format HH:MM:SS or MM:SS")
    
    @validator('url')
    def validate_youtube_url(cls, v):
        """Validate YouTube URL format"""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        if not youtube_regex.match(v):
            raise ValueError('Invalid YouTube URL format')
        return v
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        """Validate time format"""
        time_regex = re.compile(r'^(\d{1,2}:)?(\d{1,2}):(\d{2})(\.\d+)?$')
        if not time_regex.match(v):
            raise ValueError('Time must be in format HH:MM:SS, MM:SS, or include milliseconds')
        return v

class ClipResponse(BaseModel):
    """Schema for clip creation response"""
    message: str
    video_id: str
    clip_id: str
    duration: Optional[float] = None
    file_size: Optional[int] = None

class ClipDownloadResponse(BaseModel):
    """Schema for clip download information"""
    video_id: str
    filename: str
    file_size: int
    content_type: str = "video/mp4"