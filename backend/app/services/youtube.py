import asyncio
import subprocess
import os
import re
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.video import VideoDownload
from app.core.exceptions import VideoDownloadException, InvalidURLException
from app.config import settings

logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for YouTube video operations"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:v=)([0-9A-Za-z_-]{11})',
            r'youtu\.be\/([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise InvalidURLException(f"Could not extract video ID from URL: {url}")
    
    @staticmethod
    async def get_video_record(db: AsyncSession, video_id: str) -> Optional[VideoDownload]:
        """Get video record from database"""
        try:
            result = await db.execute(
                select(VideoDownload).where(
                    VideoDownload.video_id == video_id,
                    VideoDownload.is_active == True
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching video record: {e}")
            return None
    
    @staticmethod
    async def save_video_record(db: AsyncSession, video_id: str, file_path: str, file_size: int = None) -> VideoDownload:
        """Save video record to database"""
        try:
            video_record = VideoDownload(
                video_id=video_id,
                file_path=file_path,
                file_size=file_size
            )
            db.add(video_record)
            await db.commit()
            await db.refresh(video_record)
            logger.info(f"Video record saved: {video_id}")
            return video_record
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving video record: {e}")
            raise
    
    @staticmethod
    async def download_video(video_id: str, url: str) -> str:
        """Download video using yt-dlp"""
        uploads_dir = Path(settings.uploads_dir)
        output_path = uploads_dir / f"{video_id}.%(ext)s"
        
        cmd = [
            "yt-dlp",
            url,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", str(output_path),
            "--merge-output-format", "mp4",
            "--no-check-certificates",
            "--add-header", "referer:youtube.com",
            "--add-header", "user-agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--no-warnings"
        ]
        
        try:
            logger.info(f"Starting download for video ID: {video_id}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error(f"yt-dlp failed for {video_id}: {error_msg}")
                raise VideoDownloadException(f"Failed to download video: {error_msg}")
            
            # Find the downloaded file
            downloaded_file = uploads_dir / f"{video_id}.mp4"
            if not downloaded_file.exists():
                # Try to find any file with the video_id prefix
                for file in uploads_dir.glob(f"{video_id}.*"):
                    if file.suffix in ['.mp4', '.webm', '.mkv']:
                        downloaded_file = file
                        break
            
            if not downloaded_file.exists():
                raise VideoDownloadException("Downloaded file not found")
            
            logger.info(f"Video downloaded successfully: {downloaded_file}")
            return str(downloaded_file)
            
        except Exception as e:
            logger.error(f"Error downloading video {video_id}: {str(e)}")
            raise VideoDownloadException(f"Download failed: {str(e)}")