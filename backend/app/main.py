from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from app.core.database import init_db
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.config import settings

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up YouTube Clipper API...")
    await init_db()
    
    # Create uploads directory
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)
    logger.info(f"Uploads directory ready: {uploads_dir}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down YouTube Clipper API...")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="YouTube Clipper API",
        description="API for clipping YouTube videos with smart caching",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    return app

app = create_app()