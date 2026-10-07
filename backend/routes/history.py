from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from backend.services.region_service import get_region_by_identifier
from backend.services.storage_service import get_historical_observations, get_database_stats
from backend.services.preprocessing_service import analyze_data_quality, prepare_ml_dataset
from backend.models.schemas import (
    HistoricalDataResponse,
    HistoricalObservationItem,
    DataQualityResponse,
    ErrorResponse
)
from backend.utils.logger import logger

router = APIRouter(tags=["Historical Telemetry & Preprocessing"])


@router.get(
    "/history/{region_identifier}",
    response_model=HistoricalDataResponse,
    responses={404: {"model": ErrorResponse, "description": "Region not found"}}
)
def get_historical_telemetry(
    region_identifier: str,
    hours: Optional[int] = Query(default=24, ge=1, le=8760, description="Hours of historical data to retrieve"),
    start: Optional[str] = Query(default=None, description="Optional start datetime ISO filter"),
    end: Optional[str] = Query(default=None, description="Optional end datetime ISO filter"),
    limit: int = Query(default=500, ge=1, le=5000, description="Maximum observation count to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronologically sorted historical environmental observations for a region.
    Supports filtering by sliding time windows (e.g. 24h, 7d/168h, 30d/720h) or specific date bounds.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        logger.warning(f"History requested for unknown region: {region_identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    # Parse optional start/end datetimes
    dt_start = None
    dt_end = None
    if start:
        try:
            dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format. Use ISO 8601.")
    if end:
        try:
            dt_end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end date format. Use ISO 8601.")

    observations = get_historical_observations(
        db,
        region_id=region.id,
        hours=hours if (dt_start is None and dt_end is None) else None,
        start=dt_start,
        end=dt_end,
        limit=limit
    )

    range_label = f"{hours}h" if hours else "custom"

    return HistoricalDataResponse(
        success=True,
        region=region.name,
        region_id=region.id,
        range=range_label,
        count=len(observations),
        observations=observations
    )


@router.get(
    "/data-quality/{region_identifier}",
    response_model=DataQualityResponse,
    responses={404: {"model": ErrorResponse, "description": "Region not found"}}
)
def get_region_data_quality(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Performs data quality analysis on historical observations:
    computes missing value percentages, identifies invalid physical ranges,
    and flags statistical outliers using the Interquartile Range (IQR) method.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        logger.warning(f"Data quality audit requested for unknown region: {region_identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    report = analyze_data_quality(region.id, db)
    report_dict = report.to_dict()

    return DataQualityResponse(
        success=True,
        region=report.region_name,
        total_records=report.total_records,
        time_range=report.time_range,
        missing_summary=report.missing_summary,
        invalid_records_count=report.invalid_records_count,
        duplicates_removed=report.duplicates_removed,
        potential_outliers_count=report.potential_outliers_count,
        clean_records_count=report.clean_records_count
    )


@router.get("/ml-dataset/{region_identifier}")
def get_ml_ready_dataset(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Produces a clean, preprocessed, time-series dataset for a region ready for Phase 4 ML.
    Applies chronological ordering, bounds validation, missing-value imputation,
    and zero-leakage temporal, lag, and rolling features.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    dataset = prepare_ml_dataset(region.id, db)
    return {
        "success": True,
        "region": region.name,
        "region_id": region.id,
        "record_count": dataset["record_count"],
        "feature_columns": dataset["feature_columns"],
        "data": dataset["data"]
    }


@router.get("/database/stats")
def get_system_database_stats(db: Session = Depends(get_db)):
    """
    Returns actual counts, earliest/latest timestamps, and regional distribution of real observations.
    """
    stats = get_database_stats(db)
    return {
        "success": True,
        "stats": stats
    }
