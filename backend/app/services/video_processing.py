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
            
            # Convert seconds back to HH:MM:SS format for FFmpeg
            start_time_formatted = VideoProcessingService._seconds_to_time_format(start_seconds)
            end_time_formatted = VideoProcessingService._seconds_to_time_format(end_seconds)
            
            # First try with stream copy but with better keyframe handling
            cmd_copy = [
                "ffmpeg",
                "-ss", start_time_formatted,  # Seek before input for faster processing
                "-i", video_path,
                "-to", end_time_formatted,  # Use end time for accuracy
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                "-map_metadata", "-1",  # Remove metadata that might cause issues
                "-y",
                str(output_path)
            ]
            
            logger.info(f"Creating clip {clip_id} from {start_time} to {end_time} using stream copy")
            process = await asyncio.create_subprocess_exec(
                *cmd_copy,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Check if stream copy produced a valid file
            stream_copy_success = (
                process.returncode == 0 and 
                output_path.exists() and 
                output_path.stat().st_size > 1000  # At least 1KB
            )
            
            # If stream copy fails or produces small file, try re-encoding
            if not stream_copy_success:
                logger.info(f"Stream copy failed for clip {clip_id}, trying re-encoding...")
                
                # Remove failed file if exists
                if output_path.exists():
                    output_path.unlink()
                
                # Re-encoding with better compatibility settings
                cmd_encode = [
                    "ffmpeg",
                    "-ss", start_time_formatted,
                    "-i", video_path,
                    "-to", end_time_formatted,  # Use end time for accuracy
                    
                    # Video encoding settings for maximum compatibility
                    "-c:v", "libx264",
                    "-preset", "medium",  # Better quality than 'fast'
                    "-crf", "23",
                    "-profile:v", "high",  # Better than baseline, widely supported
                    "-level", "4.0",  # Modern standard level
                    "-pix_fmt", "yuv420p",
                    
                    # Audio encoding
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-ar", "44100",  # Standard sample rate
                    
                    # Container and compatibility options
                    "-movflags", "+faststart",  # Web optimization
                    "-avoid_negative_ts", "make_zero",
                    "-map_metadata", "-1",  # Remove potentially problematic metadata
                    "-fflags", "+genpts",  # Generate timestamps
                    
                    "-y",
                    str(output_path)
                ]
                
                logger.info(f"Re-encoding clip {clip_id}")
                process = await asyncio.create_subprocess_exec(
                    *cmd_encode,
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
            
            # Additional validation - try to get info about the created file
            try:
                await VideoProcessingService._validate_output_file(str(output_path))
            except Exception as e:
                logger.warning(f"Output validation failed for {clip_id}: {str(e)}")
                # Don't fail here, just log the warning
            
            logger.info(f"Clip created successfully: {output_path} (size: {output_path.stat().st_size} bytes)")
            return str(output_path), clip_id
            
        except Exception as e:
            # Clean up failed clip file
            if output_path.exists():
                try:
                    output_path.unlink()
                except:
                    pass
            
            logger.error(f"Error creating clip: {str(e)}")
            if isinstance(e, (InvalidTimeFormatException, VideoProcessingException)):
                raise
            raise VideoProcessingException(f"Clip creation failed: {str(e)}")
    
    @staticmethod
    async def _validate_output_file(file_path: str) -> None:
        """Validate that the output file is a proper video file"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-count_packets",
            "-show_entries", "stream=nb_read_packets",
            "-of", "csv=p=0",
            file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise VideoProcessingException("Generated file failed validation")
        
        try:
            packet_count = int(stdout.decode().strip())
            if packet_count == 0:
                raise VideoProcessingException("Generated file has no video packets")
        except ValueError:
            raise VideoProcessingException("Could not validate generated file")
    
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
    
    @staticmethod
    def _seconds_to_time_format(seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm format for FFmpeg"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    @staticmethod
    async def get_video_info(video_path: str) -> dict:
        """Get video information using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                raise VideoProcessingException(f"Failed to get video info: {error_msg}")
            
            import json
            info = json.loads(stdout.decode('utf-8'))
            
            # Extract useful information
            video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
            
            result = {
                'duration': float(info['format'].get('duration', 0)),
                'size': int(info['format'].get('size', 0)),
                'bitrate': int(info['format'].get('bit_rate', 0)),
            }
            
            if video_stream:
                result.update({
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'video_codec': video_stream.get('codec_name', 'unknown')
                })
            
            if audio_stream:
                result.update({
                    'audio_codec': audio_stream.get('codec_name', 'unknown'),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0))
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise VideoProcessingException(f"Failed to get video info: {str(e)}")
    
    @staticmethod 
    def validate_time_range(start_time: str, end_time: str, video_duration: float = None) -> bool:
        """Validate that the time range is valid"""
        try:
            start_seconds = VideoProcessingService._time_to_seconds(start_time)
            end_seconds = VideoProcessingService._time_to_seconds(end_time)
            
            if start_seconds < 0 or end_seconds < 0:
                raise InvalidTimeFormatException("Time values cannot be negative")
            
            if start_seconds >= end_seconds:
                raise InvalidTimeFormatException("End time must be after start time")
            
            if video_duration and end_seconds > video_duration:
                raise InvalidTimeFormatException(f"End time exceeds video duration ({video_duration}s)")
            
            duration = end_seconds - start_seconds
            if duration > settings.max_video_duration:
                raise InvalidTimeFormatException(f"Clip duration cannot exceed {settings.max_video_duration} seconds")
            
            return True
            
        except Exception as e:
            if isinstance(e, InvalidTimeFormatException):
                raise
            raise InvalidTimeFormatException(f"Invalid time range: {str(e)}")