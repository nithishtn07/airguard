from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.models.models import Region
from backend.services.storage_service import get_historical_observations
from backend.utils.logger import logger


class EnvironmentalDataQualityReport:
    """
    Represents an audit of data quality, missingness, invalid ranges, and statistical outliers.
    """
    def __init__(self, region_name: str, total_records: int):
        self.region_name = region_name
        self.total_records = total_records
        self.missing_summary: Dict[str, Dict[str, Any]] = {}
        self.invalid_records_count: int = 0
        self.duplicates_removed: int = 0
        self.potential_outliers_count: int = 0
        self.clean_records_count: int = 0
        self.time_range: Dict[str, Optional[str]] = {"start": None, "end": None}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region": self.region_name,
            "total_records": self.total_records,
            "time_range": self.time_range,
            "missing_summary": self.missing_summary,
            "invalid_records_count": self.invalid_records_count,
            "duplicates_removed": self.duplicates_removed,
            "potential_outliers_count": self.potential_outliers_count,
            "clean_records_count": self.clean_records_count
        }


def validate_physical_bounds(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Identifies and sanitizes physically impossible measurements to NaN.
    Does not invent fake replacements. Returns (sanitized_df, invalid_count).
    """
    invalid_count = 0
    df = df.copy()

    # Rule checks: (column, min_val, max_val)
    bound_rules = [
        ("aqi", 0.0, 1000.0),
        ("pm25", 0.0, 2000.0),
        ("pm10", 0.0, 3000.0),
        ("co", 0.0, 50000.0),
        ("no2", 0.0, 2000.0),
        ("so2", 0.0, 2000.0),
        ("o3", 0.0, 2000.0),
        ("temperature", -90.0, 65.0),
        ("humidity", 0.0, 100.0),
        ("wind_speed", 0.0, 400.0),
        ("pressure", 500.0, 1200.0),
        ("rainfall", 0.0, 1000.0),
    ]

    for col, min_val, max_val in bound_rules:
        if col in df.columns:
            invalid_mask = (df[col] < min_val) | (df[col] > max_val)
            cnt = int(invalid_mask.sum())
            if cnt > 0:
                invalid_count += cnt
                df.loc[invalid_mask, col] = np.nan

    return df, invalid_count


def detect_outliers_iqr(df: pd.DataFrame, target_cols: Optional[List[str]] = None) -> Tuple[pd.DataFrame, int]:
    """
    Detects statistical outliers using the Interquartile Range (IQR) method:
    Outlier if x < Q1 - 1.5*IQR or x > Q3 + 1.5*IQR.
    Note: Values are flagged for transparency without destroying genuine atmospheric pollution spikes!
    """
    df = df.copy()
    if target_cols is None:
        target_cols = [c for c in ["aqi", "pm25", "pm10", "temperature", "humidity"] if c in df.columns]

    outlier_count = 0
    df["is_potential_outlier"] = False

    for col in target_cols:
        series = df[col].dropna()
        if len(series) >= 8:  # Statistical quartiles need reasonable sample size
            q25, q75 = np.percentile(series, [25, 75])
            iqr = q75 - q25
            if iqr > 0:
                lower = q25 - 1.5 * iqr
                upper = q75 + 1.5 * iqr
                mask = (df[col] < lower) | (df[col] > upper)
                outlier_count += int(mask.sum())
                df.loc[mask, "is_potential_outlier"] = True

    return df, outlier_count


def handle_missing_values(df: pd.DataFrame, max_gap_hours: int = 2) -> pd.DataFrame:
    """
    Handles missing values in time-series environmental data.
    - Small gaps (<= max_gap_hours): uses forward fill (last observation carried forward).
    - Large gaps: strictly kept as NaN to prevent synthetic distortion of reality.
    - Does NOT fill missing values with zero!
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if "is_potential_outlier" in numeric_cols:
        numeric_cols.remove("is_potential_outlier")

    # Time-series forward fill with limited gap limit
    df[numeric_cols] = df[numeric_cols].ffill(limit=max_gap_hours)
    return df


def engineer_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates time-series features avoiding any future data leakage.
    Features:
    - hour (0-23)
    - day_of_week (0-6)
    - day (1-31)
    - month (1-12)
    - is_weekend (0 or 1)
    - Lags: aqi_lag_1, aqi_lag_3, aqi_lag_6, aqi_lag_12, aqi_lag_24
    - Rolling Means: aqi_rolling_mean_3, aqi_rolling_mean_6, aqi_rolling_mean_24
    """
    df = df.copy()
    if "timestamp" not in df.columns or len(df) == 0:
        return df

    # Ensure datetime index or column
    timestamps = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    df["hour"] = timestamps.dt.hour
    df["day_of_week"] = timestamps.dt.dayofweek
    df["day"] = timestamps.dt.day
    df["month"] = timestamps.dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # Historical lag features (strict past information: t-k, avoiding data leakage)
    if "aqi" in df.columns:
        lags = [1, 3, 6, 12, 24]
        for lag in lags:
            if len(df) > lag:
                df[f"aqi_lag_{lag}"] = df["aqi"].shift(lag)

        # Rolling past means (shift(1) ensures the current target observation t is not leaked into the window)
        rolling_windows = [3, 6, 24]
        for w in rolling_windows:
            if len(df) >= w:
                df[f"aqi_rolling_mean_{w}"] = df["aqi"].shift(1).rolling(window=w, min_periods=1).mean().round(2)

    return df


def analyze_data_quality(region_id: int, db: Session) -> EnvironmentalDataQualityReport:
    """
    Performs data quality analysis on stored observations for a region.
    Returns structured EnvironmentalDataQualityReport.
    """
    region = db.query(Region).filter(Region.id == region_id).first()
    region_name = region.name if region else f"Region #{region_id}"

    raw_records = get_historical_observations(db, region_id=region_id, limit=5000)
    total_records = len(raw_records)

    report = EnvironmentalDataQualityReport(region_name=region_name, total_records=total_records)
    if total_records == 0:
        return report

    df = pd.DataFrame(raw_records)
    report.time_range["start"] = df["timestamp"].min()
    report.time_range["end"] = df["timestamp"].max()

    # Missing value analysis
    analyzed_fields = ["aqi", "pm25", "pm10", "co", "no2", "so2", "o3", "temperature", "humidity", "wind_speed", "pressure"]
    for col in analyzed_fields:
        if col in df.columns:
            missing_count = int(df[col].isna().sum())
            missing_pct = round((missing_count / total_records) * 100.0, 2)
            report.missing_summary[col] = {
                "missing_count": missing_count,
                "missing_percentage": missing_pct,
                "present_count": total_records - missing_count
            }

    # Physical bounds validation
    sanitized_df, invalid_count = validate_physical_bounds(df)
    report.invalid_records_count = invalid_count

    # Outlier check
    _, outlier_count = detect_outliers_iqr(sanitized_df)
    report.potential_outliers_count = outlier_count

    # Clean records count
    report.clean_records_count = total_records - invalid_count

    return report


def prepare_ml_dataset(region_id: int, db: Session) -> Dict[str, Any]:
    """
    Executes the full Phase 3 preprocessing pipeline:
    Raw -> Bounds Check -> Outlier Flagging -> Missing Value Imputation -> Temporal & Lag Features.
    Returns clean ML-ready dictionary representation with feature columns.
    """
    raw_records = get_historical_observations(db, region_id=region_id, limit=5000)
    if not raw_records:
        return {
            "region_id": region_id,
            "record_count": 0,
            "feature_columns": [],
            "data": []
        }

    df = pd.DataFrame(raw_records)

    # 1. Ensure Chronological Sorting
    df["dt_temp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    df = df.sort_values("dt_temp", ascending=True).reset_index(drop=True)
    df = df.drop(columns=["dt_temp"])

    # 2. Physical boundary sanitization
    df, _ = validate_physical_bounds(df)

    # 3. Statistical outlier flagging
    df, _ = detect_outliers_iqr(df)

    # 4. Missing value handling (small-gap forward-fill)
    df = handle_missing_values(df, max_gap_hours=2)

    # 5. Temporal & Lag feature engineering (Zero leakage)
    df = engineer_temporal_features(df)

    # Convert NaNs to None for clean JSON serialization
    clean_records = df.replace({np.nan: None}).to_dict(orient="records")

    return {
        "region_id": region_id,
        "record_count": len(clean_records),
        "feature_columns": df.columns.tolist(),
        "data": clean_records
    }
