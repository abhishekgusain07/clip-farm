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
        """Download video using yt-dlp with bot detection workarounds"""
        uploads_dir = Path(settings.uploads_dir)
        output_path = uploads_dir / f"{video_id}.%(ext)s"
        
        # Base command with authentication and anti-bot measures
        cmd = [
            "yt-dlp",
            url,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", str(output_path),
            "--merge-output-format", "mp4",
            "--no-check-certificates",
            "--cookies-from-browser", "chrome",  # Use Chrome cookies for authentication
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--referer", "https://www.youtube.com/",
            "--add-header", "Accept-Language:en-US,en;q=0.9",
            "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "--sleep-interval", "1",  # Add delay to avoid rate limiting
            "--max-sleep-interval", "3",
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
                
                # Try fallback with Firefox cookies if Chrome fails
                if "Sign in to confirm you're not a bot" in error_msg or "cookies" in error_msg.lower():
                    logger.info(f"Retrying with Firefox cookies for video ID: {video_id}")
                    return await YouTubeService._download_with_fallback(video_id, url, uploads_dir, output_path)
                
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
    
    @staticmethod
    async def _download_with_fallback(video_id: str, url: str, uploads_dir: Path, output_path: Path) -> str:
        """Fallback download method with different browser cookies"""
        fallback_browsers = ["firefox", "edge", "safari"]
        
        for browser in fallback_browsers:
            try:
                logger.info(f"Trying fallback download with {browser} cookies for video ID: {video_id}")
                
                cmd = [
                    "yt-dlp",
                    url,
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "-o", str(output_path),
                    "--merge-output-format", "mp4",
                    "--no-check-certificates",
                    "--cookies-from-browser", browser,
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "--referer", "https://www.youtube.com/",
                    "--sleep-interval", "2",
                    "--max-sleep-interval", "5",
                    "--no-warnings"
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    # Find the downloaded file
                    downloaded_file = uploads_dir / f"{video_id}.mp4"
                    if not downloaded_file.exists():
                        for file in uploads_dir.glob(f"{video_id}.*"):
                            if file.suffix in ['.mp4', '.webm', '.mkv']:
                                downloaded_file = file
                                break
                    
                    if downloaded_file.exists():
                        logger.info(f"Video downloaded successfully with {browser} cookies: {downloaded_file}")
                        return str(downloaded_file)
                
            except Exception as e:
                logger.warning(f"Fallback with {browser} failed: {str(e)}")
                continue
        
        # Final fallback without cookies
        logger.info(f"Trying final fallback without cookies for video ID: {video_id}")
        try:
            cmd = [
                "yt-dlp",
                url,
                "-f", "worst[ext=mp4]/worst",  # Use worst quality as last resort
                "-o", str(output_path),
                "--merge-output-format", "mp4",
                "--no-check-certificates",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--sleep-interval", "3",
                "--max-sleep-interval", "8",
                "--no-warnings"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                downloaded_file = uploads_dir / f"{video_id}.mp4"
                if not downloaded_file.exists():
                    for file in uploads_dir.glob(f"{video_id}.*"):
                        if file.suffix in ['.mp4', '.webm', '.mkv']:
                            downloaded_file = file
                            break
                
                if downloaded_file.exists():
                    logger.info(f"Video downloaded successfully without cookies: {downloaded_file}")
                    return str(downloaded_file)
            
        except Exception as e:
            logger.error(f"Final fallback failed: {str(e)}")
        
        raise VideoDownloadException("All download methods failed. Please try again later or check if the video is publicly available.")
    
    @staticmethod
    async def create_clip(video_path: str, start_time: str, end_time: str, output_path: str) -> str:
        """Create a clip from downloaded video using ffmpeg"""
        try:
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", start_time,
                "-to", end_time,
                "-c", "copy",  # Copy without re-encoding for speed
                "-avoid_negative_ts", "make_zero",
                "-y",  # Overwrite output file
                output_path
            ]
            
            logger.info(f"Creating clip: {start_time} to {end_time}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error(f"FFmpeg failed: {error_msg}")
                raise VideoDownloadException(f"Failed to create clip: {error_msg}")
            
            if not os.path.exists(output_path):
                raise VideoDownloadException("Clip file not created")
            
            logger.info(f"Clip created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating clip: {str(e)}")
            raise VideoDownloadException(f"Clip creation failed: {str(e)}")