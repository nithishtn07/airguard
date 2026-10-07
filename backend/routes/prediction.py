"""
AirGuard AI - Machine Learning Prediction & Model APIs (Phase 4)
---------------------------------------------------------------
Endpoints:
- GET /api/prediction/{region_identifier}: Future AQI prediction
- GET /api/model/info: Model architecture, metadata, metrics, and feature importances
- GET /api/model/features: Top predictive environmental features
- POST /api/model/train: Controlled local/admin training endpoint
- POST /api/data/sync: Ingestion of genuine historical telemetry from Open-Meteo
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from backend.services.region_service import get_region_by_identifier
from backend.services.prediction_service import (
    get_prediction_for_region,
    get_model_information,
    execute_training_run
)
from backend.models.schemas import (
    PredictionResponse,
    ModelInfoResponse,
    ModelTrainResponse,
    ErrorResponse
)
from backend.utils.logger import logger
from ml.data_loader import sync_all_regions, sync_real_historical_telemetry

router = APIRouter(tags=["ML Prediction & Forecasting"])


@router.get(
    "/prediction/{region_identifier}",
    response_model=PredictionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Internal prediction error"}
    }
)
def get_predicted_aqi(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the machine learning future AQI forecast for a user-selected region.
    Integrates genuine historical observations, validates input features, and returns
    predicted AQI, directional trend, health risk category, and uncertainty bounds.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        logger.warning(f"Prediction requested for unknown region: {region_identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    res = get_prediction_for_region(region_identifier, db)
    return PredictionResponse(
        success=res.get("success", True),
        region=res.get("region", region.name),
        region_id=res.get("region_id", region.id),
        status=res.get("status", "unavailable"),
        message=res.get("message"),
        prediction=res.get("prediction")
    )


@router.get("/model/info", response_model=ModelInfoResponse)
@router.get("/model-info", response_model=ModelInfoResponse, include_in_schema=False)
def get_model_metadata_and_metrics():
    """
    Provides full academic transparency on the active ML model:
    architecture type, version, training date, number of historical observations used,
    validation metrics, test set metrics (MAE, RMSE, R²), and top feature importances.
    """
    info = get_model_information()
    return ModelInfoResponse(**info)


@router.get("/model/features")
def get_feature_importances():
    """
    Returns the ranked list of atmospheric and meteorological features
    influencing AQI predictions according to the trained model.
    """
    info = get_model_information()
    return {
        "success": True,
        "model_available": info.get("model_available", False),
        "model_type": info.get("model_type"),
        "top_features": info.get("top_features", [])
    }


@router.post("/model/train", response_model=ModelTrainResponse)
def trigger_training(
    region: Optional[str] = Query(default=None, description="Optional region name to train regional model"),
    min_rows: Optional[int] = Query(default=None, description="Override minimum row count threshold"),
    db: Session = Depends(get_db)
):
    """
    Executes controlled training of the AQI prediction model on real historical database records.
    Benchmarks the Naive Baseline against Random Forest and Gradient Boosting,
    selects the highest performing model on the validation set, and records test set metrics.
    """
    reg_id = None
    if region:
        reg = get_region_by_identifier(db, region)
        if not reg:
            raise HTTPException(status_code=404, detail=f"Region '{region}' not found.")
        reg_id = reg.id

    report = execute_training_run(region_id=reg_id, min_rows=min_rows)
    is_success = report.get("status") == "success"
    msg = (
        f"Model training succeeded: {report.get('model_type')} ({report.get('model_version')})"
        if is_success
        else report.get("message", "Model training not completed.")
    )

    return ModelTrainResponse(
        success=is_success,
        message=msg,
        report=report
    )


@router.post("/data/sync")
def sync_historical_data(
    region: Optional[str] = Query(default=None, description="Optional specific region to sync"),
    days: int = Query(default=7, ge=1, le=30, description="Past days of genuine telemetry to sync"),
    db: Session = Depends(get_db)
):
    """
    Ingests genuine historical environmental observations from Copernicus CAMS & Open-Meteo
    into the SQLite database. Strictly real atmospheric observations with deduplication.
    """
    if region:
        reg = get_region_by_identifier(db, region)
        if not reg:
            raise HTTPException(status_code=404, detail=f"Region '{region}' not found.")
        count = sync_real_historical_telemetry(db, reg, past_days=days)
        return {
            "success": True,
            "message": f"Synced {count} genuine historical observations for {reg.name}.",
            "counts": {reg.name: count}
        }
    else:
        counts = sync_all_regions(db, past_days=days)
        total = sum(counts.values())
        return {
            "success": True,
            "message": f"Synced {total} genuine historical observations across all regions.",
            "counts": counts
        }
