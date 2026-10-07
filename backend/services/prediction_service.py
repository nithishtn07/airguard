"""
AirGuard AI - Prediction Service (Phase 4)
------------------------------------------
Bridges the FastAPI application with the Phase 4 ML pipeline.
Retrieves real stored observations, prepares runtime features,
executes model inference, and logs forecasts to the database.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session

from backend.models.models import Region, Prediction, utc_now
from backend.services.storage_service import get_historical_observations
from backend.services.region_service import get_region_by_identifier
from backend.utils.logger import logger
from ml.model_registry import model_registry
from ml.feature_engineering import prepare_features, FEATURE_COLUMNS
from ml.prediction.predictor import predictor
from ml.train import train_aqi_model


def get_prediction_for_region(region_identifier: str, db: Session) -> Dict[str, Any]:
    """
    Computes real-time future AQI prediction for a region.
    Integrates directly with genuine stored observations.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        return {
            "success": False,
            "region": region_identifier,
            "region_id": -1,
            "status": "unavailable",
            "message": f"Region '{region_identifier}' not found."
        }

    # 1. Verify model availability
    if not model_registry.is_available():
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "status": "unavailable",
            "message": "Model has not been trained because sufficient historical data is not yet available.",
            "prediction": None
        }

    # 2. Retrieve recent observations to construct lag/rolling features
    # Need enough rows to compute rolling means and lags
    raw_obs = get_historical_observations(db, region_id=region.id, limit=50)
    if not raw_obs or len(raw_obs) < 2:
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "status": "unavailable",
            "message": "More historical observations are required before reliable prediction can be generated.",
            "prediction": None
        }

    df = pd.DataFrame(raw_obs)

    # 3. Feature engineering on latest sequence
    df_prepared = prepare_features(df)
    if df_prepared.empty:
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "status": "unavailable",
            "message": "Required recent environmental data is currently unavailable.",
            "prediction": None
        }

    # The most recent row is our prediction input (representing state t)
    latest_row = df_prepared.iloc[-1]
    feature_dict = latest_row.to_dict()
    current_aqi = float(latest_row["aqi"]) if "aqi" in latest_row and pd.notna(latest_row["aqi"]) else None
    obs_time = str(latest_row.get("timestamp", ""))

    # 4. Model inference via Predictor
    pred_result = predictor.predict(
        feature_vector=feature_dict,
        current_aqi=current_aqi,
        observation_time_iso=obs_time
    )

    if pred_result.get("status") != "available":
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "status": "unavailable",
            "message": pred_result.get("message", "Prediction temporarily unavailable."),
            "prediction": None
        }

    # 5. Persist prediction record in relational database
    try:
        forecast_dt = datetime.fromisoformat(pred_result["forecast_time"].replace("Z", "+00:00"))
        pred_record = Prediction(
            region_id=region.id,
            prediction_time=utc_now(),
            forecast_time=forecast_dt,
            predicted_aqi=pred_result["predicted_aqi"],
            model_version=pred_result["model_version"]
        )
        db.add(pred_record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Non-blocking error saving prediction record: {e}")

    return {
        "success": True,
        "region": region.name,
        "region_id": region.id,
        "status": "available",
        "message": "Prediction successfully generated using trained ML model.",
        "prediction": pred_result
    }


def get_model_information() -> Dict[str, Any]:
    """
    Exposes model metadata, performance evaluation metrics,
    and top predictive features for academic transparency.
    """
    metadata = model_registry.get_metadata()
    if not metadata:
        return {
            "success": True,
            "model_available": False,
            "status_message": "No trained machine learning model available. Training requires sufficient real historical data."
        }

    metrics = metadata.get("metrics", {})
    val_metrics = metrics.get("selected_validation")
    test_metrics = metrics.get("test")

    return {
        "success": True,
        "model_available": True,
        "model_type": metadata.get("model_type"),
        "model_version": metadata.get("model_version"),
        "target": metadata.get("target"),
        "trained_at": metadata.get("trained_at"),
        "training_rows": metadata.get("training_rows", 0),
        "validation_rows": metadata.get("validation_rows", 0),
        "test_rows": metadata.get("test_rows", 0),
        "features": metadata.get("features", []),
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "top_features": metadata.get("top_features", []),
        "status_message": "Model active and serving predictions."
    }


def execute_training_run(region_id: Optional[int] = None, min_rows: Optional[int] = None) -> Dict[str, Any]:
    """
    Triggers model training run on real database records.
    """
    result = train_aqi_model(region_id=region_id, min_rows=min_rows)
    return result
