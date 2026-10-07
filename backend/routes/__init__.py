from fastapi import APIRouter
from backend.routes.health import router as health_router
from backend.routes.regions import router as regions_router
from backend.routes.environment import router as environment_router
from backend.routes.history import router as history_router
from backend.routes.prediction import router as prediction_router
from backend.routes.intelligence import router as intelligence_router
from backend.routes.risk import router as risk_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.environmental_insights import router as environmental_insights_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(regions_router)
api_router.include_router(environment_router)
api_router.include_router(history_router)
api_router.include_router(prediction_router)
api_router.include_router(intelligence_router)
api_router.include_router(risk_router)
api_router.include_router(dashboard_router)
api_router.include_router(environmental_insights_router)

__all__ = ["api_router"]

