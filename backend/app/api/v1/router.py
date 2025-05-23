
from fastapi import APIRouter
from app.api.v1.endpoints import clip, health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

api_router.include_router(
    clip.router,
    prefix="/clip",
    tags=["clip"]
)