
import uvicorn
from app.config import settings

def run_dev():
    """Run development server"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        access_log=True
    )

if __name__ == "__main__":
    run_dev()
