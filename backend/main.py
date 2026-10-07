import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import settings
from backend.utils.logger import logger
from backend.services.region_service import init_db_and_seed
from backend.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown procedures.
    """
    logger.info(f"Initializing {settings.APP_NAME} (Phase {settings.PHASE})...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    # Database initialization & initial region seeding
    try:
        init_db_and_seed()
        logger.info("Database initialized and region registry verified.")
    except Exception as e:
        logger.error(f"Critical error initializing database: {e}")
        # In development, keep running so health check can report degraded state

    yield

    logger.info(f"Shutting down {settings.APP_NAME} cleanly.")


# Instantiate FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-Time Air Quality Monitoring, ML Prediction, Hotspot/Anomaly Detection, Risk Engine & Environmental Intelligence Dashboard",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers Middleware (Phase 8 Optimization)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# =====================================================================
# ERROR HANDLERS (Step 15 - Clean & Safe Error Responses)
# =====================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request payload or query parameter.",
            "errors": exc.errors() if settings.DEBUG else []
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    detail_msg = str(exc) if settings.DEBUG else "An unexpected internal server error occurred."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail_msg, "status_code": 500}
    )


# =====================================================================
# ROUTERS & STATIC FRONTEND
# =====================================================================

# Register API Router
app.include_router(api_router)

# Mount frontend directories if they exist
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the AirGuard AI landing page."""
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({
        "message": f"Welcome to {settings.APP_NAME}",
        "status": "online",
        "phase": settings.PHASE,
        "docs": "/docs"
    })


def _serve_page(filename: str):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    # Graceful fallback to index.html if specific page file is missing
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index_file)


@app.get("/dashboard", include_in_schema=False)
async def serve_dashboard():
    return _serve_page("dashboard.html")


@app.get("/air-quality", include_in_schema=False)
async def serve_air_quality():
    return _serve_page("air_quality.html")


@app.get("/predictions", include_in_schema=False)
async def serve_predictions():
    return _serve_page("predictions.html")


@app.get("/hotspots", include_in_schema=False)
async def serve_hotspots():
    return _serve_page("hotspots.html")


@app.get("/anomalies", include_in_schema=False)
async def serve_anomalies():
    return _serve_page("anomalies.html")


@app.get("/risk", include_in_schema=False)
async def serve_risk():
    return _serve_page("risk.html")


@app.get("/recommendations", include_in_schema=False)
async def serve_recommendations():
    return _serve_page("recommendations.html")


@app.get("/environmental-insights", include_in_schema=False)
async def serve_environmental_insights():
    return _serve_page("environmental_insights.html")


@app.get("/alerts", include_in_schema=False)
async def serve_alerts():
    return _serve_page("alerts.html")


@app.get("/map", include_in_schema=False)
async def serve_map():
    return _serve_page("map.html")


@app.get("/history", include_in_schema=False)
async def serve_history():
    return _serve_page("history.html")


@app.get("/settings", include_in_schema=False)
async def serve_settings():
    return _serve_page("settings.html")

