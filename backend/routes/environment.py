from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from backend.services.region_service import get_region_by_identifier
from backend.services.air_quality_service import fetch_live_air_quality
from backend.services.weather_service import fetch_live_weather
from backend.services.storage_service import (
    save_air_quality_observation,
    save_weather_observation,
    save_environmental_snapshot
)
from backend.models.schemas import (
    AirQualityResponse,
    WeatherResponse,
    EnvironmentResponse,
    ErrorResponse
)
from backend.utils.logger import logger

router = APIRouter(tags=["Real-Time Environment"])


@router.get(
    "/air-quality/{region_identifier}",
    response_model=AirQualityResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        503: {"model": ErrorResponse, "description": "Upstream air quality service unavailable"},
        504: {"model": ErrorResponse, "description": "Upstream service timeout"}
    }
)
def get_current_air_quality(
    region_identifier: str,
    refresh: bool = Query(default=False, description="Bypass cache and force live fetch"),
    db: Session = Depends(get_db)
):
    """
    Retrieves real-time atmospheric air quality telemetry for a user-selected region.
    Automatically persists observation to historical database with duplicate prevention.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        logger.warning(f"Air quality requested for unknown region: {region_identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        data = fetch_live_air_quality(region, force_refresh=refresh)
        # Automatic historical persistence (Phase 3)
        try:
            save_air_quality_observation(db, region.id, data)
        except Exception as se:
            logger.warning(f"Non-blocking storage error for air quality: {se}")

        return AirQualityResponse(
            success=True,
            data=data,
            source=data.source
        )
    except TimeoutError as te:
        logger.error(f"Timeout in air quality endpoint: {te}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(te))
    except Exception as e:
        logger.error(f"Error retrieving air quality for {region.name}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get(
    "/weather/{region_identifier}",
    response_model=WeatherResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        503: {"model": ErrorResponse, "description": "Upstream weather service unavailable"},
        504: {"model": ErrorResponse, "description": "Upstream service timeout"}
    }
)
def get_current_weather(
    region_identifier: str,
    refresh: bool = Query(default=False, description="Bypass cache and force live fetch"),
    db: Session = Depends(get_db)
):
    """
    Retrieves real-time meteorological conditions for a user-selected region.
    Automatically persists observation to historical database with duplicate prevention.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        logger.warning(f"Weather requested for unknown region: {region_identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        data = fetch_live_weather(region, force_refresh=refresh)
        # Automatic historical persistence (Phase 3)
        try:
            save_weather_observation(db, region.id, data)
        except Exception as se:
            logger.warning(f"Non-blocking storage error for weather: {se}")

        return WeatherResponse(
            success=True,
            data=data,
            source=data.source
        )
    except TimeoutError as te:
        logger.error(f"Timeout in weather endpoint: {te}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(te))
    except Exception as e:
        logger.error(f"Error retrieving weather for {region.name}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get(
    "/environment/{region_identifier}",
    response_model=EnvironmentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        503: {"model": ErrorResponse, "description": "Upstream environmental service unavailable"},
        504: {"model": ErrorResponse, "description": "Upstream service timeout"}
    }
)
def get_combined_environment(
    region_identifier: str,
    refresh: bool = Query(default=False, description="Bypass cache and force live fetch"),
    db: Session = Depends(get_db)
):
    """
    Unified environmental endpoint returning both real-time air quality and weather telemetry.
    Automatically persists environmental snapshot to historical database.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        logger.warning(f"Environment requested for unknown region: {region_identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        aq_data = fetch_live_air_quality(region, force_refresh=refresh)
        weather_data = fetch_live_weather(region, force_refresh=refresh)

        # Automatic historical persistence (Phase 3)
        try:
            save_environmental_snapshot(db, region.id, aq_data, weather_data)
        except Exception as se:
            logger.warning(f"Non-blocking storage error for snapshot: {se}")

        return EnvironmentResponse(
            success=True,
            region=region.name,
            region_id=region.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            air_quality=aq_data,
            weather=weather_data
        )
    except TimeoutError as te:
        logger.error(f"Timeout in combined environment endpoint: {te}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(te))
    except Exception as e:
        logger.error(f"Error retrieving environment for {region.name}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
