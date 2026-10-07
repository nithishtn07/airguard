"""
AirGuard AI - Model Evaluation & Comparison Module (Phase 4)
------------------------------------------------------------
Implements regression metrics (MAE, RMSE, R2), the naive persistence baseline,
and comparative performance benchmarking.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes standard regression metrics:
    - MAE: Mean Absolute Error
    - RMSE: Root Mean Squared Error
    - R²: Coefficient of Determination
    - MAPE: Mean Absolute Percentage Error (with epsilon safety)
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    # Filter any NaNs if present
    valid_mask = (~np.isnan(y_true)) & (~np.isnan(y_pred))
    y_t = y_true[valid_mask]
    y_p = y_pred[valid_mask]

    if len(y_t) == 0:
        return {"mae": 0.0, "rmse": 0.0, "r2": 0.0, "mape": 0.0}

    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))

    # Handle R2 edge case where variance of y_true is near zero
    if np.var(y_t) == 0:
        r2 = 1.0 if np.allclose(y_t, y_p) else 0.0
    else:
        r2 = float(r2_score(y_t, y_p))

    # Safe MAPE with epsilon = 1.0 to avoid division by zero
    epsilon = 1.0
    mape = float(np.mean(np.abs((y_t - y_p) / np.maximum(np.abs(y_t), epsilon))) * 100.0)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "mape": round(mape, 2)
    }


class NaiveBaselinePredictor:
    """
    Academic Persistence Baseline:
    Predicts next-step AQI(t+1) = AQI(t) (i.e. the current observation remains constant).
    In our feature matrix, AQI(t) is represented by 'aqi_lag_1' (or current AQI).
    """
    def __init__(self, fallback_val: float = 100.0):
        self.fallback_val = fallback_val

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "aqi_lag_1" in X.columns:
            preds = X["aqi_lag_1"].copy()
            preds = preds.fillna(self.fallback_val)
            return preds.values.astype(float)
        elif "aqi" in X.columns:
            preds = X["aqi"].copy()
            preds = preds.fillna(self.fallback_val)
            return preds.values.astype(float)
        else:
            return np.full(len(X), self.fallback_val, dtype=float)


def format_model_comparison_table(model_results: Dict[str, Dict[str, float]]) -> str:
    """
    Renders an academic comparison table of all evaluated models.
    """
    header = f"{'Model':<24} | {'MAE':<8} | {'RMSE':<8} | {'R²':<8}"
    divider = "-" * len(header)
    rows = [divider, header, divider]

    for model_name, metrics in model_results.items():
        mae_str = f"{metrics.get('mae', 0.0):.2f}"
        rmse_str = f"{metrics.get('rmse', 0.0):.2f}"
        r2_str = f"{metrics.get('r2', 0.0):.4f}"
        rows.append(f"{model_name:<24} | {mae_str:<8} | {rmse_str:<8} | {r2_str:<8}")

    rows.append(divider)
    return "\n".join(rows)


def extract_feature_importances(model: Any, feature_names: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts feature importance weights from fitted tree-based models.
    Returns sorted list from most predictive to least.
    """
    if not hasattr(model, "feature_importances_"):
        return []

    raw_importances = model.feature_importances_
    results = []

    # Human-readable parameter descriptions
    desc_map = {
        "pm25": "Fine Particulate Matter 2.5 µg/m³",
        "pm10": "Coarse Particulate Matter 10 µg/m³",
        "co": "Carbon Monoxide µg/m³",
        "no2": "Nitrogen Dioxide µg/m³",
        "so2": "Sulphur Dioxide µg/m³",
        "o3": "Surface Ozone µg/m³",
        "temperature": "Ambient Temperature °C",
        "humidity": "Relative Atmospheric Humidity %",
        "wind_speed": "Wind Velocity km/h",
        "wind_direction": "Wind Direction Degrees",
        "pressure": "Barometric Surface Pressure hPa",
        "rainfall": "Precipitation Accumulation mm",
        "aqi_lag_1": "1-Step Prior AQI Observation",
        "aqi_lag_3": "3-Step Prior AQI Observation",
        "aqi_lag_6": "6-Step Prior AQI Observation",
        "aqi_rolling_mean_3": "3-Observation Rolling AQI Mean",
        "aqi_rolling_mean_6": "6-Observation Rolling AQI Mean",
        "pm25_rolling_mean_3": "3-Observation Rolling PM2.5 Mean",
        "pm10_rolling_mean_3": "3-Observation Rolling PM10 Mean",
        "hour": "Hour of Day (0-23)",
        "day_of_week": "Day of Week (0-6)",
        "month": "Month of Year (1-12)",
        "is_weekend": "Weekend Binary Indicator",
        "hour_sin": "Cyclical Hour (Sine Transform)",
        "hour_cos": "Cyclical Hour (Cosine Transform)",
        "day_of_week_sin": "Cyclical Day of Week (Sine)",
        "day_of_week_cos": "Cyclical Day of Week (Cosine)",
    }

    for name, imp in zip(feature_names, raw_importances):
        results.append({
            "feature": name,
            "importance": round(float(imp), 4),
            "description": desc_map.get(name, "Environmental Variable")
        })

    # Sort descending by importance weight
    results.sort(key=lambda x: x["importance"], reverse=True)
    return results
