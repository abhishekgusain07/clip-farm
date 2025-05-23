from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.sql import func
from app.core.database import Base

class VideoDownload(Base):
    """Model for tracking downloaded videos"""
    __tablename__ = "video_downloads"
    
    video_id = Column(String(20), primary_key=True, index=True)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)
    
    def __repr__(self):
        return f"<VideoDownload(video_id='{self.video_id}', file_path='{self.file_path}')>"