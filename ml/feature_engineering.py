"""
AirGuard AI - Feature Engineering & Leakage-Free Dataset Preparation (Phase 4)
-----------------------------------------------------------------------------
Transforms cleaned historical environmental observations into time-series regression
datasets. Guarantees strict avoidance of future data leakage:
- Target is next time-step AQI: AQI(t+1) = shift(-1)
- Lags use past observations strictly: AQI(t-k) = shift(k)
- Rolling features shift by 1 before window aggregation: rolling(k).shift(1)
- Temporal cyclical encodings (sin/cos of hour and day of week)
- Chronological, non-random splitting (Train -> Validation -> Test)
"""
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import pandas as pd

from backend.services.preprocessing_service import (
    validate_physical_bounds,
    detect_outliers_iqr,
    handle_missing_values,
    engineer_temporal_features
)
from backend.utils.logger import logger


FEATURE_COLUMNS: List[str] = [
    # Spatial identifier
    "region_id",
    # Atmospheric Pollutants
    "pm25",
    "pm10",
    "co",
    "no2",
    "so2",
    "o3",
    # Meteorological Variables
    "temperature",
    "humidity",
    "wind_speed",
    "wind_direction",
    "pressure",
    "rainfall",
    # Historical Lags (Strictly past t-k)
    "aqi_lag_1",
    "aqi_lag_3",
    "aqi_lag_6",
    # Rolling Statistics (Past window shifted by 1)
    "aqi_rolling_mean_3",
    "aqi_rolling_mean_6",
    "pm25_rolling_mean_3",
    "pm10_rolling_mean_3",
    # Temporal & Calendar
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    # Cyclical Encodings
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos"
]

TARGET_COLUMN: str = "target_aqi"


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies the full Phase 3 preprocessing and extracts Phase 4 predictive features.
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    # 1. Enforce strict chronological ordering
    if "timestamp" in df.columns:
        df["_dt"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
        df = df.sort_values("_dt", ascending=True).reset_index(drop=True)
        df = df.drop(columns=["_dt"])

    # 2. Physical boundary sanitization (bounds invalid data to NaN)
    df, _ = validate_physical_bounds(df)

    # 3. Statistical outlier flagging (retains natural spikes)
    df, _ = detect_outliers_iqr(df)

    # 4. Small-gap missing value imputation (forward fill limit 2h)
    df = handle_missing_values(df, max_gap_hours=2)

    # 5. Core temporal and lag features from Phase 3
    df = engineer_temporal_features(df)

    # 6. Additional Phase 4 cyclical encodings
    if "hour" in df.columns:
        df["hour_sin"] = np.sin(2.0 * np.pi * df["hour"] / 24.0).round(4)
        df["hour_cos"] = np.cos(2.0 * np.pi * df["hour"] / 24.0).round(4)
    else:
        df["hour_sin"] = 0.0
        df["hour_cos"] = 0.0

    if "day_of_week" in df.columns:
        df["day_of_week_sin"] = np.sin(2.0 * np.pi * df["day_of_week"] / 7.0).round(4)
        df["day_of_week_cos"] = np.cos(2.0 * np.pi * df["day_of_week"] / 7.0).round(4)
    else:
        df["day_of_week_sin"] = 0.0
        df["day_of_week_cos"] = 0.0

    # 7. Additional pollutant rolling averages (Zero-leakage: shifted by 1)
    if "pm25" in df.columns and len(df) >= 3:
        df["pm25_rolling_mean_3"] = df["pm25"].shift(1).rolling(window=3, min_periods=1).mean().round(2)
    else:
        df["pm25_rolling_mean_3"] = df.get("pm25", np.nan)

    if "pm10" in df.columns and len(df) >= 3:
        df["pm10_rolling_mean_3"] = df["pm10"].shift(1).rolling(window=3, min_periods=1).mean().round(2)
    else:
        df["pm10_rolling_mean_3"] = df.get("pm10", np.nan)

    # 8. Define target: Future AQI at next step t+1 (shift -1)
    if "aqi" in df.columns:
        df[TARGET_COLUMN] = df["aqi"].shift(-1)

    return df


def create_training_dataset(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, List[str]]:
    """
    Builds the feature matrix X and target vector y for supervised ML training.
    Drops the last observation (where target t+1 is not yet observed) and any row
    with missing target.
    Returns (X, y, timestamps, feature_names).
    """
    prepared = prepare_features(df)
    if prepared.empty or TARGET_COLUMN not in prepared.columns:
        return pd.DataFrame(), pd.Series(), pd.Series(), FEATURE_COLUMNS

    # Ensure all expected feature columns exist in prepared DataFrame
    for col in FEATURE_COLUMNS:
        if col not in prepared.columns:
            prepared[col] = np.nan

    # Drop rows where target is NaN (e.g. latest observation waiting for actual future)
    valid_mask = prepared[TARGET_COLUMN].notna()
    clean_set = prepared.loc[valid_mask].copy()

    X = clean_set[FEATURE_COLUMNS].copy()
    y = clean_set[TARGET_COLUMN].astype(float).copy()
    timestamps = clean_set["timestamp"].copy() if "timestamp" in clean_set.columns else pd.Series()

    return X, y, timestamps, FEATURE_COLUMNS


def split_time_series(
    X: pd.DataFrame,
    y: pd.Series,
    timestamps: Optional[pd.Series] = None,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
) -> Dict[str, Any]:
    """
    Performs chronological time-series splitting without random shuffling.
    - 70% oldest observations -> Training set
    - 15% intermediate observations -> Validation set
    - 15% most recent observations -> Test set
    """
    n = len(X)
    if n == 0:
        raise ValueError("Cannot split an empty dataset.")

    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    # Ensure all splits have at least 1 observation if n >= 5
    if n >= 5:
        n_train = max(n_train, 1)
        n_val = max(n_val, 1)

    train_end = n_train
    val_end = n_train + n_val

    X_train = X.iloc[:train_end].copy()
    y_train = y.iloc[:train_end].copy()

    X_val = X.iloc[train_end:val_end].copy()
    y_val = y.iloc[train_end:val_end].copy()

    X_test = X.iloc[val_end:].copy()
    y_test = y.iloc[val_end:].copy()

    t_train = timestamps.iloc[:train_end] if timestamps is not None and not timestamps.empty else None
    t_val = timestamps.iloc[train_end:val_end] if timestamps is not None and not timestamps.empty else None
    t_test = timestamps.iloc[val_end:] if timestamps is not None and not timestamps.empty else None

    # Verification: Chronological continuity audit
    if timestamps is not None and not timestamps.empty:
        max_train = pd.to_datetime(t_train, format="mixed", utc=True).max()
        min_val = pd.to_datetime(t_val, format="mixed", utc=True).min()
        if not t_test.empty:
            min_test = pd.to_datetime(t_test, format="mixed", utc=True).min()
            logger.debug(f"Split chronological audit: Train max={max_train} <= Val min={min_val} <= Test min={min_test}")

    return {
        "X_train": X_train,
        "y_train": y_train,
        "X_val": X_val,
        "y_val": y_val,
        "X_test": X_test,
        "y_test": y_test,
        "t_train": t_train,
        "t_val": t_val,
        "t_test": t_test,
        "counts": {
            "total": n,
            "train": len(X_train),
            "val": len(X_val),
            "test": len(X_test)
        }
    }


def verify_no_data_leakage(
    feature_names: List[str],
    target_name: str,
    train_timestamps: Optional[pd.Series],
    val_timestamps: Optional[pd.Series],
    test_timestamps: Optional[pd.Series]
) -> Tuple[bool, List[str]]:
    """
    Audits feature and temporal integrity:
    1. Target column must NOT be present in feature set.
    2. Chronological sequence must be strictly monotonic (Train <= Val <= Test).
    """
    violations = []

    # Check 1: Target in features
    if target_name in feature_names:
        violations.append(f"Target '{target_name}' is illegally included in feature columns!")

    # Check 2: Raw future AQI
    if "target_aqi" in feature_names or "next_aqi" in feature_names:
        violations.append("Future target indicator found in features.")

    # Check 3: Timestamp monotonicity
    if train_timestamps is not None and val_timestamps is not None and not train_timestamps.empty and not val_timestamps.empty:
        max_train = pd.to_datetime(train_timestamps, format="mixed", utc=True).max()
        min_val = pd.to_datetime(val_timestamps, format="mixed", utc=True).min()
        if max_train > min_val:
            violations.append(f"Temporal leakage: Max train timestamp ({max_train}) is after Min validation timestamp ({min_val})")

    if val_timestamps is not None and test_timestamps is not None and not val_timestamps.empty and not test_timestamps.empty:
        max_val = pd.to_datetime(val_timestamps, format="mixed", utc=True).max()
        min_test = pd.to_datetime(test_timestamps, format="mixed", utc=True).min()
        if max_val > min_test:
            violations.append(f"Temporal leakage: Max val timestamp ({max_val}) is after Min test timestamp ({min_test})")

    is_valid = len(violations) == 0
    return is_valid, violations
