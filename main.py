"""
AirGuard AI - Main Application Runner
Convenience entry point for running the application locally.
"""
import uvicorn
from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
