import asyncio
import subprocess
import os
import uuid
from pathlib import Path
from typing import Tuple
import logging

from app.core.exceptions import VideoProcessingException, InvalidTimeFormatException
from app.config import settings

logger = logging.getLogger(__name__)

class VideoProcessingService:
    """Service for video processing operations"""
    
    @staticmethod
    async def create_clip(video_path: str, start_time: str, end_time: str) -> Tuple[str, str]:
        """Create a clip from the video and return (clip_path, clip_id)"""
        clip_id = str(uuid.uuid4())
        output_path = Path(settings.uploads_dir) / f"clip_{clip_id}.mp4"
        
        try:
            # Convert time format if needed
            start_seconds = VideoProcessingService._time_to_seconds(start_time)
            end_seconds = VideoProcessingService._time_to_seconds(end_time)
            duration = end_seconds - start_seconds
            
            if duration <= 0:
                raise InvalidTimeFormatException("End time must be after start time")
            
            if duration > settings.max_video_duration:
                raise InvalidTimeFormatException(f"Clip duration cannot exceed {settings.max_video_duration} seconds")
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(start_seconds),
                "-t", str(duration),
                "-c:v", "libx264",
                "-profile:v", "high",
                "-level", "4.0",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                "-avoid_negative_ts", "make_zero",
                "-y",  # Overwrite output file
                str(output_path)
            ]
            
            logger.info(f"Creating clip {clip_id} from {start_time} to {end_time}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error(f"FFmpeg failed for clip {clip_id}: {error_msg}")
                raise VideoProcessingException(f"Failed to create clip: {error_msg}")
            
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise VideoProcessingException("Clip creation failed - output file is missing or empty")
            
            logger.info(f"Clip created successfully: {output_path}")
            return str(output_path), clip_id
            
        except Exception as e:
            logger.error(f"Error creating clip: {str(e)}")
            if isinstance(e, (InvalidTimeFormatException, VideoProcessingException)):
                raise
            raise VideoProcessingException(f"Clip creation failed: {str(e)}")
    
    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        """Convert time string to seconds"""
        try:
            parts = time_str.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            else:
                raise ValueError("Invalid time format")
        except (ValueError, IndexError) as e:
            raise InvalidTimeFormatException(f"Invalid time format '{time_str}': {str(e)}")