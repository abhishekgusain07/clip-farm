
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging

from app.schemas.clip import ClipRequest, ClipResponse
from app.services.youtube import YouTubeService
from app.services.video_processing import VideoProcessingService
from app.services.file_manager import FileManagerService
from app.api.deps import get_database
from app.core.exceptions import (
    VideoDownloadException, 
    VideoProcessingException, 
    InvalidURLException,
    InvalidTimeFormatException,
    create_http_exception
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=ClipResponse)
async def create_clip(
    request: ClipRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
):
    """
    Create a clip from a YouTube video.
    Downloads the video if not already cached in the database.
    """
    try:
        # Extract YouTube video ID
        video_id = YouTubeService.extract_video_id(request.url)
        logger.info(f"Processing clip request for video ID: {video_id}")
        
        # Check if video is already downloaded
        video_record = await YouTubeService.get_video_record(db, video_id)
        video_path = None
        
        if not video_record:
            logger.info(f"Video {video_id} not found in database, downloading...")
            
            # Download the video
            video_path = await YouTubeService.download_video(video_id, request.url)
            
            # Get file size
            file_size = FileManagerService.get_file_size(video_path)
            
            # Save to database
            await YouTubeService.save_video_record(db, video_id, video_path, file_size)
            logger.info(f"Video {video_id} downloaded and saved to database")
        else:
            video_path = video_record.file_path
            if not os.path.exists(video_path):
                logger.warning(f"Video file {video_path} missing, re-downloading...")
                video_path = await YouTubeService.download_video(video_id, request.url)
                file_size = FileManagerService.get_file_size(video_path)
                video_record.file_path = video_path
                video_record.file_size = file_size
                await db.commit()
        
        # Create the clip
        clip_path, clip_id = await VideoProcessingService.create_clip(
            video_path, 
            request.start_time, 
            request.end_time
        )
        
        # Get clip file size
        clip_size = FileManagerService.get_file_size(clip_path)
        
        # Schedule cleanup after 1 hour
        background_tasks.add_task(
            FileManagerService.cleanup_file, 
            clip_path
        )
        
        return ClipResponse(
            message="Clip created successfully",
            video_id=video_id,
            clip_id=clip_id,
            file_size=clip_size
        )
        
    except InvalidURLException as e:
        logger.error(f"Invalid URL: {str(e)}")
        raise create_http_exception(400, "Invalid YouTube URL", {"url": request.url})
    
    except InvalidTimeFormatException as e:
        logger.error(f"Invalid time format: {str(e)}")
        raise create_http_exception(400, "Invalid time format", {"error": str(e)})
    
    except VideoDownloadException as e:
        logger.error(f"Video download failed: {str(e)}")
        raise create_http_exception(500, "Failed to download video", {"error": str(e)})
    
    except VideoProcessingException as e:
        logger.error(f"Video processing failed: {str(e)}")
        raise create_http_exception(500, "Failed to process video", {"error": str(e)})
    
    except Exception as e:
        logger.error(f"Unexpected error processing clip request: {str(e)}")
        raise create_http_exception(500, "Internal server error", {"error": "An unexpected error occurred"})

@router.get("/download/{clip_id}")
async def download_clip(clip_id: str):
    """
    Download a clipped video file by clip ID.
    """
    clip_path = f"uploads/clip_{clip_id}.mp4"
    
    if not os.path.exists(clip_path):
        logger.warning(f"Clip not found: {clip_id}")
        raise create_http_exception(404, "Clip not found", {"clip_id": clip_id})
    
    return FileResponse(
        path=clip_path,
        filename=f"clip_{clip_id}.mp4",
        media_type="video/mp4"
    )