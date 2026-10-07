"""
AirGuard AI - Environmental Risk Assessment Engine (Phase 6)
-------------------------------------------------------------
Combines multi-modal atmospheric signals from Phases 2-5 into an explainable,
deterministic, and configurable Composite Environmental Risk Score (0 - 100).

Signals evaluated:
1. Current AQI severity (Phase 2)
2. Predicted next-step AQI forecast (Phase 4)
3. Particulate matter toxicity (PM2.5 & PM10) (Phase 2/3)
4. Pollution hotspot severity & persistence (Phase 5 Part A)
5. Statistical pollution anomaly departures (Phase 5 Part B)

Distinction:
- AQI: Direct atmospheric concentration index
- Hotspot: Spatial/relative elevation across regions
- Anomaly: Temporal departure from historical baseline
- Risk: Multi-factor environmental & health safety exposure index
"""
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from config.settings import settings
from backend.models.models import Region, AirQualityObservation
from backend.services.region_service import get_region_by_identifier
from backend.services.hotspot_service import get_regional_hotspot_detail
from backend.services.anomaly_service import detect_anomalies_for_region
from backend.services.prediction_service import get_prediction_for_region
from backend.utils.logger import logger


def calculate_risk_level_and_color(score: float) -> Tuple[str, str]:
    """
    Maps a composite risk score (0.0 - 100.0) into configured categorical tiers.
    """
    if score is None or math.isnan(score):
        return "UNKNOWN", "#6b7280"

    score = float(score)
    if score <= settings.RISK_LOW_MAX:
        return "LOW", "#10b981"
    elif score <= settings.RISK_MODERATE_MAX:
        return "MODERATE", "#f59e0b"
    elif score <= settings.RISK_HIGH_MAX:
        return "HIGH", "#ea580c"
    elif score <= settings.RISK_VERY_HIGH_MAX:
        return "VERY HIGH", "#dc2626"
    else:
        return "CRITICAL", "#7f1d1d"


def normalize_aqi_component(aqi: Optional[float], max_ref: float = 300.0) -> Optional[float]:
    """Normalizes an AQI reading onto a 0 - 100 scale."""
    if aqi is None or math.isnan(aqi):
        return None
    return float(min(100.0, max(0.0, (aqi / max_ref) * 100.0)))


def normalize_particulate_component(
    pm25: Optional[float],
    pm10: Optional[float]
) -> Optional[float]:
    """
    Normalizes particulate matter concentrations onto a 0 - 100 toxicity scale.
    PM2.5 reference: 150 µg/m³ (Severe health impact threshold)
    PM10 reference: 300 µg/m³ (Severe health impact threshold)
    """
    s_pm25 = None
    s_pm10 = None

    if pm25 is not None and not math.isnan(pm25):
        s_pm25 = min(100.0, max(0.0, (pm25 / 150.0) * 100.0))
    if pm10 is not None and not math.isnan(pm10):
        s_pm10 = min(100.0, max(0.0, (pm10 / 300.0) * 100.0))

    if s_pm25 is not None and s_pm10 is not None:
        return float(round(0.65 * s_pm25 + 0.35 * s_pm10, 2))
    elif s_pm25 is not None:
        return float(round(s_pm25, 2))
    elif s_pm10 is not None:
        return float(round(s_pm10, 2))
    return None


def assess_environmental_risk(
    db: Session,
    region_identifier: Any
) -> Dict[str, Any]:
    """
    Performs comprehensive, explainable environmental risk assessment for a monitored region.
    Integrates actual stored records, live ML forecasts, hotspot ranking, and anomaly detection.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise ValueError(f"Region '{region_identifier}' not found in registry.")

    logger.info(f"Assessing environmental risk for region '{region.name}' (ID: {region.id})")

    # 1. Fetch latest real atmospheric observation from database
    latest_aq = (
        db.query(AirQualityObservation)
        .filter(AirQualityObservation.region_id == region.id)
        .order_by(AirQualityObservation.timestamp.desc())
        .first()
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # If no live/stored telemetry exists at all for this region
    if not latest_aq or latest_aq.aqi is None:
        logger.warning(f"No air quality observations found for {region.name}; risk assessment unavailable.")
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "timestamp": now_iso,
            "risk_score": 0.0,
            "risk_level": "UNAVAILABLE",
            "risk_color": "#6b7280",
            "confidence": None,
            "reasons": ["Risk assessment unavailable because sufficient live data is unavailable."],
            "contributors": {
                "current_aqi": 0.0,
                "predicted_aqi": None,
                "pollutants": None,
                "hotspot": None,
                "anomaly": None
            },
            "data_available": False,
            "model_version": settings.RISK_MODEL
        }

    current_aqi = float(latest_aq.aqi)
    pm25 = float(latest_aq.pm2_5) if latest_aq.pm2_5 is not None else None
    pm10 = float(latest_aq.pm10) if latest_aq.pm10 is not None else None

    # 2. Fetch ML future prediction (Phase 4)
    pred_res = get_prediction_for_region(region.id, db)
    pred_data = pred_res.get("prediction") if pred_res.get("status") == "available" else None
    predicted_aqi = float(pred_data["predicted_aqi"]) if pred_data and "predicted_aqi" in pred_data else None

    # 3. Fetch Hotspot status (Phase 5 Part A)
    hotspot_detail = get_regional_hotspot_detail(db, region.id)
    hotspot_score = float(hotspot_detail.get("hotspot_score", 0.0)) if hotspot_detail else 0.0
    hotspot_level = hotspot_detail.get("level", "NORMAL") if hotspot_detail else "NORMAL"

    # 4. Fetch Anomaly status (Phase 5 Part B)
    anomaly_res = detect_anomalies_for_region(db, region.id, persist=False)
    highest_anomaly_score = float(anomaly_res.get("highest_anomaly_score", 0.0))
    anomaly_status = anomaly_res.get("anomaly_status", "NORMAL")

    # 5. Calculate normalized component scores (0 - 100)
    s_current_aqi = normalize_aqi_component(current_aqi)
    s_predicted_aqi = normalize_aqi_component(predicted_aqi) if predicted_aqi is not None else None
    s_pollutants = normalize_particulate_component(pm25, pm10)
    s_hotspot = min(100.0, max(0.0, hotspot_score * 100.0))
    s_anomaly = min(100.0, max(0.0, highest_anomaly_score * 100.0))

    # 6. Configurable multi-modal weights with dynamic availability redistribution
    # Base configuration:
    # Current AQI: 35%, Predicted AQI: 20%, Pollutants: 20%, Hotspot: 15%, Anomaly: 10%
    base_components = {
        "current_aqi": (0.35, s_current_aqi),
        "predicted_aqi": (0.20, s_predicted_aqi),
        "pollutants": (0.20, s_pollutants),
        "hotspot": (0.15, s_hotspot),
        "anomaly": (0.10, s_anomaly)
    }

    # Filter available non-None components
    available_components = {
        k: (weight, score)
        for k, (weight, score) in base_components.items()
        if score is not None
    }

    total_avail_weight = sum(weight for weight, _ in available_components.values())
    if total_avail_weight <= 0:
        total_avail_weight = 1.0

    # Compute weighted composite score
    composite_raw = sum(
        (weight / total_avail_weight) * score
        for weight, score in available_components.values()
    )
    risk_score = float(round(min(100.0, max(0.0, composite_raw)), 1))
    risk_level, risk_color = calculate_risk_level_and_color(risk_score)

    # 7. Generate transparent, data-backed reasons
    reasons: List[str] = []

    # Current AQI reason
    if current_aqi >= 200:
        reasons.append(f"Current AQI is very high ({round(current_aqi)}), driving severe exposure risk.")
    elif current_aqi >= 100:
        reasons.append(f"Current AQI is elevated ({round(current_aqi)}), exceeding standard clean air thresholds.")
    elif current_aqi <= 50:
        reasons.append(f"Current AQI is favorable ({round(current_aqi)}), contributing to low baseline risk.")

    # PM2.5 / PM10 particulate reason
    if pm25 is not None and pm25 >= 60.0:
        reasons.append(f"Fine particulate matter (PM2.5: {round(pm25, 1)} µg/m³) is significantly elevated.")
    elif pm10 is not None and pm10 >= 100.0:
        reasons.append(f"Coarse particulate matter (PM10: {round(pm10, 1)} µg/m³) exceeds standard limits.")

    # Future prediction reason
    if predicted_aqi is not None:
        pred_trend = pred_data.get("trend", "STABLE") if pred_data else "STABLE"
        if pred_trend == "WORSENING" or predicted_aqi > current_aqi + 15:
            reasons.append(f"ML forecast indicates deteriorating conditions (predicted AQI: {round(predicted_aqi, 1)}).")
        elif pred_trend == "IMPROVING" and predicted_aqi < current_aqi - 15:
            reasons.append(f"ML forecast anticipates improving air quality (predicted AQI: {round(predicted_aqi, 1)}).")

    # Hotspot reason
    if hotspot_level in ("HOTSPOT", "SEVERE HOTSPOT"):
        reasons.append(f"Region is classified as an active pollution hotspot ({hotspot_level}).")
    elif hotspot_level == "ELEVATED":
        reasons.append("Region exhibits elevated pollution relative to other monitored centers.")

    # Anomaly reason
    if anomaly_status in ("HIGH ANOMALY", "EXTREME ANOMALY"):
        reasons.append(f"Statistically significant pollution departure detected ({anomaly_status}).")
    elif anomaly_status == "UNUSUAL":
        reasons.append("Unusual divergence from regional historical baseline detected.")

    if not reasons:
        reasons.append("Atmospheric readings across monitored pollutants align with safe baseline levels.")

    # Contributors dictionary with both raw component scores and contributions
    contributors = {
        "current_aqi": round(s_current_aqi, 1) if s_current_aqi is not None else 0.0,
        "predicted_aqi": round(s_predicted_aqi, 1) if s_predicted_aqi is not None else None,
        "pollutants": round(s_pollutants, 1) if s_pollutants is not None else None,
        "hotspot": round(s_hotspot, 1) if s_hotspot is not None else None,
        "anomaly": round(s_anomaly, 1) if s_anomaly is not None else None,
        "weights_applied": {
            k: round(weight / total_avail_weight, 3)
            for k, (weight, _) in available_components.items()
        }
    }

    obs_timestamp = latest_aq.timestamp.isoformat() if latest_aq.timestamp else now_iso

    return {
        "success": True,
        "region": region.name,
        "region_id": region.id,
        "timestamp": obs_timestamp,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "confidence": None,  # Strictly None as per academic rules (never fake)
        "reasons": reasons,
        "contributors": contributors,
        "data_available": True,
        "model_version": settings.RISK_MODEL
    }
