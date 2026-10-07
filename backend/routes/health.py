from datetime import datetime, timezone
from fastapi import APIRouter
from config.settings import settings
from database.session import check_db_connection
from backend.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health_status():
    """
    Health check endpoint to verify backend status and database connectivity.
    """
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        application=settings.APP_NAME,
        phase=settings.PHASE,
        environment=settings.ENVIRONMENT,
        database_connected=db_ok,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
