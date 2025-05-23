from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/youtube_clipper"
    
    # Application
    debug: bool = False
    secret_key: str = "your-secret-key-change-in-production"
    allowed_hosts: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # File storage
    uploads_dir: str = "uploads"
    max_video_duration: int = 3600  # 1 hour in seconds
    max_file_size: int = 1073741824  # 1GB in bytes
    
    # External services
    youtube_api_key: str = ""
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()