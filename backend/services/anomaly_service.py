"""
AirGuard AI - Pollution Anomaly Detection Service (Phase 5)
-----------------------------------------------------------
Identifies unusual pollution behavior compared with the normal historical baseline
of a specific monitored region.

Preserves the fundamental distinction:
- Hotspot: Where pollution is consistently or currently elevated (spatial / relative).
- Anomaly: When pollution behaves unusually relative to historical baseline (temporal deviation).

Includes:
- Strict zero-leakage statistical rolling analysis (past observations only).
- Safe zero-variance / zero standard deviation handling.
- Multi-pollutant analysis (AQI, PM2.5, PM10, NO2, SO2, O3, CO).
- Configurable Z-score thresholds and normalized anomaly scoring.
- Explainable natural language diagnostic outputs.
- Timeline generation with baseline means and upper statistical envelopes.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc

from config.settings import settings
from backend.models.models import Region, Anomaly, utc_now
from backend.services.storage_service import get_historical_observations
from backend.services.region_service import get_region_by_identifier
from backend.utils.logger import logger


# Metric display definitions and units
METRIC_UNITS = {
    "aqi": "Index",
    "pm25": "µg/m³",
    "pm10": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "o3": "µg/m³",
    "co": "µg/m³"
}

METRIC_LABELS = {
    "aqi": "AQI",
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "so2": "SO2",
    "o3": "O3",
    "co": "CO"
}


def calculate_anomaly_severity_and_color(
    z_score: float,
    threshold: Optional[float] = None
) -> Tuple[str, str, bool]:
    """
    Classifies a statistical Z-score into explainable anomaly severity levels.
    
    Levels:
    - NORMAL: |z| < 2.0 (Within standard historical variability)
    - UNUSUAL: 2.0 <= |z| < threshold (Noticeable drift from baseline)
    - HIGH ANOMALY: threshold <= |z| < 3.5 (Statistically significant spike)
    - EXTREME ANOMALY: |z| >= 3.5 (Severe statistical departure)
    """
    z_abs = abs(z_score)
    thresh = threshold or settings.ANOMALY_Z_THRESHOLD

    if z_abs >= 3.5:
        return "EXTREME ANOMALY", "#dc2626", True
    elif z_abs >= thresh:
        return "HIGH ANOMALY", "#ea580c", True
    elif z_abs >= 2.0:
        return "UNUSUAL", "#d97706", False
    else:
        return "NORMAL", "#10b981", False


def calculate_anomaly_score(z_score: float) -> float:
    """
    Maps a Z-score onto a normalized 0.0 to 1.0 scale for cross-metric comparison.
    NOTE: This is an empirical Anomaly Score, NOT a calibrated event probability.
    """
    return round(float(min(1.0, max(0.0, abs(z_score) / 4.0))), 2)


def compute_z_score_safe(
    observed_value: float,
    baseline_values: List[float]
) -> Tuple[float, float, float]:
    """
    Safely computes Z-score against a baseline series with strict zero-variance handling.
    Returns: (z_score, baseline_mean, baseline_std)
    """
    if not baseline_values:
        return 0.0, observed_value, 0.0

    mean_val = float(np.mean(baseline_values))
    std_val = float(np.std(baseline_values))

    # Safe zero standard deviation handling
    if std_val < 1e-6:
        if abs(observed_value - mean_val) < 1e-6:
            return 0.0, mean_val, 0.0
        else:
            # Constant baseline suddenly broken
            dev = observed_value - mean_val
            pseudo_z = 3.0 if dev > 0 else -3.0
            return pseudo_z, mean_val, 0.0

    z = (observed_value - mean_val) / std_val
    return float(z), mean_val, std_val


def generate_anomaly_explanation(
    metric_key: str,
    observed_val: float,
    baseline_mean: float,
    baseline_std: float,
    z_score: float,
    severity: str
) -> str:
    """
    Generates an explainable, fact-based textual diagnosis of an anomaly.
    """
    label = METRIC_LABELS.get(metric_key, metric_key.upper())
    unit = METRIC_UNITS.get(metric_key, "")
    deviation = observed_val - baseline_mean
    sign = "+" if deviation >= 0 else ""

    if severity in ("HIGH ANOMALY", "EXTREME ANOMALY"):
        if deviation > 0:
            return (
                f"{label} spiked to {round(observed_val, 1)} {unit}. "
                f"Historical baseline mean is {round(baseline_mean, 1)} {unit} (deviation: {sign}{round(deviation, 1)} {unit}, "
                f"Z-score: {round(z_score, 2)}). Severe departure from normal regional atmospheric patterns."
            )
        else:
            return (
                f"{label} fell sharply to {round(observed_val, 1)} {unit}. "
                f"Historical baseline mean is {round(baseline_mean, 1)} {unit} (deviation: {round(deviation, 1)} {unit}, "
                f"Z-score: {round(z_score, 2)}). Unusually clean atmospheric clearance."
            )
    elif severity == "UNUSUAL":
        return (
            f"{label} observed at {round(observed_val, 1)} {unit} differs noticeably from baseline mean of "
            f"{round(baseline_mean, 1)} {unit} (Z-score: {round(z_score, 2)})."
        )
    else:
        return (
            f"{label} ({round(observed_val, 1)} {unit}) is consistent with local baseline mean "
            f"({round(baseline_mean, 1)} ± {round(baseline_std, 1)} {unit})."
        )


def evaluate_metric_anomaly(
    metric_key: str,
    latest_val: Optional[float],
    historical_series: List[float],
    timestamp: str,
    z_thresh: float
) -> Optional[Dict[str, Any]]:
    """
    Evaluates anomaly metrics for a single pollutant or AQI value.
    """
    if latest_val is None or len(historical_series) < 3:
        return None

    z_score, mean_val, std_val = compute_z_score_safe(latest_val, historical_series)
    severity, color, is_anomaly = calculate_anomaly_severity_and_color(z_score, z_thresh)
    score = calculate_anomaly_score(z_score)
    deviation = latest_val - mean_val

    explanation = generate_anomaly_explanation(
        metric_key=metric_key,
        observed_val=latest_val,
        baseline_mean=mean_val,
        baseline_std=std_val,
        z_score=z_score,
        severity=severity
    )

    return {
        "timestamp": timestamp,
        "metric": METRIC_LABELS.get(metric_key, metric_key.upper()),
        "metric_key": metric_key,
        "observed_value": round(latest_val, 2),
        "expected_value": round(mean_val, 2),
        "baseline_std": round(std_val, 2),
        "z_score": round(z_score, 2),
        "anomaly_score": score,
        "severity": severity,
        "severity_color": color,
        "deviation": round(deviation, 2),
        "is_anomaly": is_anomaly,
        "reason": explanation
    }


def detect_anomalies_for_region(
    db: Session,
    region_identifier: Any,
    hours: Optional[int] = None,
    z_threshold: Optional[float] = None,
    persist: bool = True
) -> Dict[str, Any]:
    """
    Comprehensive anomaly detection for a specific region.
    
    1. Validates historical record volume against minimum requirements.
    2. Evaluates latest observation across priority pollutants (AQI, PM2.5, PM10).
    3. Builds rolling zero-leakage timeline for chronological visualization.
    4. Persists verified high/extreme anomalies into database.
    """
    thresh = z_threshold or settings.ANOMALY_Z_THRESHOLD
    region = get_region_by_identifier(db, region_identifier)

    if not region:
        raise ValueError(f"Region '{region_identifier}' not found in registry.")

    logger.info(f"Anomaly analysis started for region '{region.name}' (threshold={thresh})")

    # Fetch chronological observations (limit to recent bounded window)
    window_hours = hours or (settings.ANOMALY_ROLLING_WINDOW * 3)  # Look back enough to establish robust baseline
    raw_obs = get_historical_observations(db, region_id=region.id, hours=window_hours, limit=500)

    # If hours filter returned too few, fallback to all recent observations for this region
    if len(raw_obs) < settings.MIN_ANOMALY_OBSERVATIONS:
        raw_obs = get_historical_observations(db, region_id=region.id, hours=None, limit=200)

    total_obs = len(raw_obs)

    # Minimum data validation rule
    if total_obs < settings.MIN_ANOMALY_OBSERVATIONS:
        logger.warning(
            f"Insufficient historical data for region '{region.name}': {total_obs} observations found, "
            f"minimum required: {settings.MIN_ANOMALY_OBSERVATIONS}"
        )
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "latitude": region.latitude,
            "longitude": region.longitude,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "method": settings.ANOMALY_METHOD,
            "z_threshold": thresh,
            "observations_analyzed": total_obs,
            "has_anomalies": False,
            "anomaly_status": "NORMAL",
            "highest_anomaly_score": 0.0,
            "message": f"Insufficient historical data for reliable anomaly analysis ({total_obs}/{settings.MIN_ANOMALY_OBSERVATIONS} observations).",
            "anomalies": [],
            "timeline": []
        }

    # Latest observation
    latest_record = raw_obs[-1]
    latest_timestamp = latest_record.get("timestamp")
    if isinstance(latest_timestamp, datetime):
        latest_ts_str = latest_timestamp.isoformat()
    else:
        latest_ts_str = str(latest_timestamp or datetime.now(timezone.utc).isoformat())

    # Build historical baseline series strictly excluding the latest point (Zero Leakage)
    baseline_records = raw_obs[:-1]
    
    # Priority pollutants to inspect
    priority_metrics = ["aqi", "pm25", "pm10", "no2", "so2", "o3", "co"]
    detected_anomalies: List[Dict[str, Any]] = []
    all_metric_evals: List[Dict[str, Any]] = []

    for metric in priority_metrics:
        # Extract valid non-null numerical values from baseline records
        baseline_vals = [
            float(r[metric]) for r in baseline_records
            if r.get(metric) is not None and not np.isnan(float(r[metric]))
        ]
        
        latest_val = latest_record.get(metric)
        if latest_val is not None:
            latest_val = float(latest_val)

        eval_result = evaluate_metric_anomaly(
            metric_key=metric,
            latest_val=latest_val,
            historical_series=baseline_vals,
            timestamp=latest_ts_str,
            z_thresh=thresh
        )

        if eval_result:
            all_metric_evals.append(eval_result)
            if eval_result["is_anomaly"]:
                detected_anomalies.append(eval_result)

    # Chronological timeline calculation with strictly causal rolling baseline (Zero Leakage)
    # Uses rolling window up to 24 points prior to each observation
    timeline: List[Dict[str, Any]] = []
    rolling_window = settings.ANOMALY_ROLLING_WINDOW

    # Take the most recent 36 points for visualization
    sample_records = raw_obs[-36:] if len(raw_obs) > 36 else raw_obs

    for i, rec in enumerate(sample_records):
        ts = rec.get("timestamp")
        ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        aqi_val = float(rec["aqi"]) if rec.get("aqi") is not None else None
        pm25_val = float(rec["pm25"]) if rec.get("pm25") is not None else None
        pm10_val = float(rec["pm10"]) if rec.get("pm10") is not None else None

        # Build baseline strictly from prior points in raw_obs
        # Index of rec in full raw_obs
        full_idx = len(raw_obs) - len(sample_records) + i
        prior_window_records = raw_obs[max(0, full_idx - rolling_window):full_idx]

        valid_prior_aqi = [
            float(r["aqi"]) for r in prior_window_records
            if r.get("aqi") is not None and not np.isnan(float(r["aqi"]))
        ]

        if valid_prior_aqi and len(valid_prior_aqi) >= 3 and aqi_val is not None:
            mean_pt = float(np.mean(valid_prior_aqi))
            std_pt = float(np.std(valid_prior_aqi))
            upper_bound = round(mean_pt + (thresh * max(std_pt, 2.0)), 1)
            
            z_pt, _, _ = compute_z_score_safe(aqi_val, valid_prior_aqi)
            sev_pt, _, is_anom_pt = calculate_anomaly_severity_and_color(z_pt, thresh)
        else:
            mean_pt = aqi_val
            upper_bound = None
            is_anom_pt = False
            sev_pt = "NORMAL"

        timeline.append({
            "timestamp": ts_str,
            "aqi": aqi_val,
            "pm25": pm25_val,
            "pm10": pm10_val,
            "baseline_aqi": round(mean_pt, 1) if mean_pt is not None else None,
            "upper_bound_aqi": upper_bound,
            "is_anomaly": is_anom_pt,
            "anomaly_severity": sev_pt if is_anom_pt else None
        })

    # Overall region anomaly status determination
    if any(a["severity"] == "EXTREME ANOMALY" for a in detected_anomalies):
        overall_status = "EXTREME ANOMALY"
    elif any(a["severity"] == "HIGH ANOMALY" for a in detected_anomalies):
        overall_status = "HIGH ANOMALY"
    elif any(e["severity"] == "UNUSUAL" for e in all_metric_evals):
        overall_status = "UNUSUAL"
    else:
        overall_status = "NORMAL"

    highest_score = max([e["anomaly_score"] for e in all_metric_evals], default=0.0)

    # Persist genuine detected anomalies into database if requested
    if persist and detected_anomalies:
        for anom in detected_anomalies:
            try:
                # Check for existing duplicate anomaly record (same region, timestamp, pollutant)
                obs_dt = datetime.fromisoformat(anom["timestamp"].replace("Z", "+00:00"))
                exists = (
                    db.query(Anomaly)
                    .filter(
                        Anomaly.region_id == region.id,
                        Anomaly.timestamp == obs_dt,
                        Anomaly.pollutant == anom["metric"]
                    )
                    .first()
                )
                if not exists:
                    db_anom = Anomaly(
                        region_id=region.id,
                        timestamp=obs_dt,
                        pollutant=anom["metric"],
                        observed_value=anom["observed_value"],
                        expected_value=anom["expected_value"],
                        anomaly_score=anom["anomaly_score"],
                        severity=anom["severity"]
                    )
                    db.add(db_anom)
                    db.commit()
                    anom["id"] = db_anom.id
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not persist anomaly record: {e}")

    logger.info(
        f"Anomaly analysis completed for region '{region.name}': "
        f"{len(detected_anomalies)} anomalies flagged, overall status: {overall_status}"
    )

    return {
        "success": True,
        "region": region.name,
        "region_id": region.id,
        "latitude": region.latitude,
        "longitude": region.longitude,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": settings.ANOMALY_METHOD,
        "z_threshold": thresh,
        "observations_analyzed": total_obs,
        "has_anomalies": len(detected_anomalies) > 0,
        "anomaly_status": overall_status,
        "highest_anomaly_score": highest_score,
        "anomalies": detected_anomalies,
        "timeline": timeline
    }


def assess_all_anomalies(
    db: Session,
    hours: Optional[int] = None,
    z_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates anomaly detection across all active monitored regions.
    """
    thresh = z_threshold or settings.ANOMALY_Z_THRESHOLD
    regions = db.query(Region).filter(Region.is_active == True).all()

    regional_results = []
    total_anomalies = 0

    for r in regions:
        res = detect_anomalies_for_region(
            db=db,
            region_identifier=r.id,
            hours=hours,
            z_threshold=thresh,
            persist=False
        )
        regional_results.append(res)
        total_anomalies += len(res.get("anomalies", []))

    return {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": settings.ANOMALY_METHOD,
        "z_threshold": thresh,
        "total_regions": len(regions),
        "total_anomalies_detected": total_anomalies,
        "regions": regional_results
    }
