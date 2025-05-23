
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

async def get_database() -> AsyncSession:
    """Get database session dependency"""
    async for db in get_db():
        yield db

def get_current_user():
    """Get current user dependency (placeholder for future auth)"""
    # TODO: Implement authentication
    return {"user_id": "anonymous"}