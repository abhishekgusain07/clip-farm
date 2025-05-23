
import uvicorn
from app.config import settings

def run_prod():
    """Run production server"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level="info",
        access_log=False
    )

if __name__ == "__main__":
    run_prod()
