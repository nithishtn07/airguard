"""
AirGuard AI - Machine Learning Prediction Interface & Implementation (Phase 4)
-------------------------------------------------------------------------------
Executes validated model inference, calculates ensemble uncertainty spreads,
assigns AQI health risk categories, and determines directional trend.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd

from backend.utils.logger import logger
from ml.model_registry import model_registry


def get_aqi_category_and_color(aqi_val: float) -> Tuple[str, str]:
    """
    Maps a numeric AQI to its standard health advisory category and visual color code.
    (Aligned with US EPA / National AQI Standards)
    """
    if aqi_val <= 50.0:
        return "Good", "#10b981"
    elif aqi_val <= 100.0:
        return "Moderate", "#f59e0b"
    elif aqi_val <= 150.0:
        return "Unhealthy for Sensitive Groups", "#f97316"
    elif aqi_val <= 200.0:
        return "Unhealthy", "#ef4444"
    elif aqi_val <= 300.0:
        return "Very Unhealthy", "#8b5cf6"
    else:
        return "Hazardous", "#7f1d1d"


class BaseAQIPredictor(ABC):
    @abstractmethod
    def predict(self, feature_vector: Any) -> Dict[str, Any]:
        """Generate predicted AQI and confidence bounds."""
        pass


class AirGuardAQIPredictor(BaseAQIPredictor):
    """
    Production-ready AQI Predictor implementing BaseAQIPredictor.
    Utilizes trained model package from ModelRegistry with feature alignment and validation.
    """
    def __init__(self):
        self.registry = model_registry

    def predict(
        self,
        feature_vector: Dict[str, Any],
        current_aqi: Optional[float] = None,
        observation_time_iso: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes prediction with input sanitization, uncertainty calculation,
        and trend assessment.
        """
        package = self.registry.load_active_model()
        if not package:
            return {
                "status": "unavailable",
                "message": "Model has not been trained because sufficient historical data is not yet available."
            }

        model = package["model"]
        imputer = package.get("imputer")
        expected_features: List[str] = package["features"]
        model_type = package.get("model_type", "MLModel")
        model_version = package.get("model_version", "v1")

        # 1. Feature Order Alignment & Validation
        row_vals = []
        for feat in expected_features:
            val = feature_vector.get(feat, np.nan)
            if val is not None:
                try:
                    fval = float(val)
                    if np.isinf(fval):
                        fval = np.nan
                except (ValueError, TypeError):
                    fval = np.nan
            else:
                fval = np.nan
            row_vals.append(fval)

        df_in = pd.DataFrame([row_vals], columns=expected_features)

        # 2. Impute any missing features using trained imputer
        try:
            if imputer is not None:
                X_mat = imputer.transform(df_in)
            else:
                X_mat = df_in.fillna(0.0).values
        except Exception as e:
            logger.error(f"Error during feature imputation: {e}")
            return {
                "status": "error",
                "message": "Required environmental features are currently incomplete or invalid."
            }

        # 3. Model Inference
        try:
            pred_raw = model.predict(X_mat)[0]
        except Exception as e:
            logger.error(f"Inference error in {model_type}: {e}")
            return {
                "status": "error",
                "message": "Internal error generating model prediction."
            }

        # Sanity check: Ensure finite and non-negative
        if np.isnan(pred_raw) or np.isinf(pred_raw):
            return {
                "status": "error",
                "message": "Model produced an invalid non-finite value."
            }

        predicted_aqi = max(0.0, round(float(pred_raw), 1))

        # 4. Uncertainty Estimation
        # For Random Forest: standard deviation across individual tree predictions
        std_dev = None
        lower_bound = None
        upper_bound = None

        if hasattr(model, "estimators_") and len(model.estimators_) > 0:
            try:
                tree_preds = [tree.predict(X_mat)[0] for tree in model.estimators_]
                std_dev = round(float(np.std(tree_preds)), 1)
                lower_bound = max(0.0, round(predicted_aqi - 1.96 * std_dev, 1))
                upper_bound = round(predicted_aqi + 1.96 * std_dev, 1)
            except Exception as e:
                logger.debug(f"Tree variance calculation skipped: {e}")

        # Fallback to validation/test RMSE if available
        if std_dev is None:
            metrics = package.get("metrics", {})
            test_rmse = metrics.get("test", {}).get("rmse") or metrics.get("selected_validation", {}).get("rmse")
            if test_rmse is not None:
                std_dev = round(float(test_rmse), 1)
                lower_bound = max(0.0, round(predicted_aqi - std_dev, 1))
                upper_bound = round(predicted_aqi + std_dev, 1)

        # 5. Trend Analysis
        trend = "STABLE"
        trend_delta = None
        if current_aqi is not None and not np.isnan(current_aqi):
            current_aqi = round(float(current_aqi), 1)
            diff = round(predicted_aqi - current_aqi, 1)
            trend_delta = abs(diff)
            if diff > 3.0:
                trend = "INCREASING"
            elif diff < -3.0:
                trend = "DECREASING"
            else:
                trend = "STABLE"

        # 6. AQI Health Category
        category, category_color = get_aqi_category_and_color(predicted_aqi)

        # 7. Timestamps
        now_utc = datetime.now(timezone.utc)
        if observation_time_iso:
            try:
                base_time = datetime.fromisoformat(observation_time_iso.replace("Z", "+00:00"))
            except Exception:
                base_time = now_utc
        else:
            base_time = now_utc

        # Next time-step forecast horizon (+1 hour)
        forecast_time = base_time + timedelta(hours=1)

        return {
            "status": "available",
            "target": "next_step_aqi",
            "predicted_aqi": predicted_aqi,
            "current_aqi": current_aqi,
            "trend": trend,
            "trend_delta": trend_delta,
            "confidence_bound_lower": lower_bound,
            "confidence_bound_upper": upper_bound,
            "uncertainty_spread": std_dev,
            "category": category,
            "category_color": category_color,
            "prediction_time": now_utc.isoformat(),
            "forecast_time": forecast_time.isoformat(),
            "model_type": model_type,
            "model_version": model_version
        }


# Global predictor instance
predictor = AirGuardAQIPredictor()
