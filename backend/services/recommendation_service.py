"""
AirGuard AI - Smart Health & Safety Recommendations Engine (Phase 6)
-------------------------------------------------------------------
Generates actionable, data-driven, and context-aware advisories
based on actual real-time environmental measurements, ML forecasts,
and detected anomalies/hotspots.

Strict Guidelines:
- Non-diagnostic advisory tone (no medical guarantees or claims).
- Highly contextual (prioritizes critical risk, high PM2.5, worsening trends, etc.).
- Categorized and priority-ranked (HIGH, MEDIUM, LOW).
- Deduplicated and concise (prevents spammy, repetitive advice).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.models import Region, AirQualityObservation, WeatherObservation
from backend.services.region_service import get_region_by_identifier
from backend.services.risk_service import assess_environmental_risk
from backend.services.hotspot_service import get_regional_hotspot_detail
from backend.services.anomaly_service import detect_anomalies_for_region
from backend.services.prediction_service import get_prediction_for_region
from backend.utils.logger import logger


def generate_recommendations(
    db: Session,
    region_identifier: Any
) -> Dict[str, Any]:
    """
    Synthesizes environmental context to produce prioritized, deduplicated recommendations.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise ValueError(f"Region '{region_identifier}' not found.")

    logger.info(f"Generating smart recommendations for region '{region.name}'")

    # 1. Fetch risk assessment
    risk_info = assess_environmental_risk(db, region.id)
    now_iso = datetime.now(timezone.utc).isoformat()

    if not risk_info.get("data_available", False):
        return {
            "success": True,
            "region": region.name,
            "region_id": region.id,
            "generated_at": now_iso,
            "risk_level": "UNAVAILABLE",
            "risk_score": 0.0,
            "data_available": False,
            "total_recommendations": 1,
            "recommendations": [
                {
                    "id": "rec_insufficient_data",
                    "priority": "LOW",
                    "category": "GENERAL",
                    "title": "Data Unavailable",
                    "message": "Personalized recommendation unavailable because sufficient environmental data is unavailable.",
                    "reason": "Live sensor telemetry has not yet been recorded for this region.",
                    "icon": "ℹ️"
                }
            ]
        }

    risk_score = risk_info.get("risk_score", 0.0)
    risk_level = risk_info.get("risk_level", "LOW")

    # 2. Fetch latest telemetry details
    latest_aq = (
        db.query(AirQualityObservation)
        .filter(AirQualityObservation.region_id == region.id)
        .order_by(AirQualityObservation.timestamp.desc())
        .first()
    )
    latest_weather = (
        db.query(WeatherObservation)
        .filter(WeatherObservation.region_id == region.id)
        .order_by(WeatherObservation.timestamp.desc())
        .first()
    )

    current_aqi = latest_aq.aqi if latest_aq else None
    pm25 = latest_aq.pm2_5 if latest_aq else None
    pm10 = latest_aq.pm10 if latest_aq else None

    # 3. Fetch prediction details
    pred_res = get_prediction_for_region(region.id, db)
    pred_data = pred_res.get("prediction") if pred_res.get("status") == "available" else None
    pred_trend = pred_data.get("trend") if pred_data else None
    predicted_aqi = pred_data.get("predicted_aqi") if pred_data else None

    # 4. Fetch anomaly and hotspot details
    anomaly_res = detect_anomalies_for_region(db, region.id, persist=False)
    anomaly_status = anomaly_res.get("anomaly_status", "NORMAL")

    hotspot_detail = get_regional_hotspot_detail(db, region.id)
    hotspot_level = hotspot_detail.get("level", "NORMAL") if hotspot_detail else "NORMAL"

    recommendations: List[Dict[str, Any]] = []
    seen_messages = set()

    def add_rec(rec_id: str, priority: str, category: str, title: str, message: str, reason: str, icon: str):
        norm_key = (category, message.strip().lower())
        if norm_key not in seen_messages:
            seen_messages.add(norm_key)
            recommendations.append({
                "id": rec_id,
                "priority": priority,
                "category": category,
                "title": title,
                "message": message,
                "reason": reason,
                "icon": icon
            })

    # Rule Group A: Critical & High Risk / Severe Exposure
    if risk_level in ("CRITICAL", "VERY HIGH"):
        add_rec(
            rec_id="rec_critical_exposure",
            priority="HIGH",
            category="EXPOSURE",
            title="Limit Outdoor Exposure",
            message="Consider minimizing prolonged or strenuous outdoor exposure until air quality metrics improve.",
            reason=f"Current composite environmental risk is classified as {risk_level} (Score: {risk_score}/100).",
            icon="🚨"
        )
        add_rec(
            rec_id="rec_mask_advisory",
            priority="HIGH",
            category="MASK",
            title="Protective Respiratory Awareness",
            message="Consider wearing a well-fitted particulate respirator (such as N95/FFP2) when venturing outdoors.",
            reason=f"Atmospheric particulate concentrations present heightened exposure risk in this region.",
            icon="😷"
        )
    elif risk_level == "HIGH":
        add_rec(
            rec_id="rec_high_activity",
            priority="HIGH",
            category="OUTDOOR_ACTIVITY",
            title="Reduce Strenuous Outdoor Exercise",
            message="Consider shifting intense athletic training or heavy outdoor exertion indoors.",
            reason="Elevated air pollution levels increase respiratory intake during vigorous aerobic exercise.",
            icon="⚠️"
        )
    elif risk_level == "MODERATE":
        add_rec(
            rec_id="rec_moderate_awareness",
            priority="MEDIUM",
            category="OUTDOOR_ACTIVITY",
            title="Outdoor Activity with Awareness",
            message="Outdoor activity is generally permissible, though sensitive individuals should monitor comfort levels.",
            reason="Air quality is in the moderate range; routine exposure is acceptable for most healthy adults.",
            icon="🏃"
        )
    else:  # LOW risk
        add_rec(
            rec_id="rec_low_risk_enjoy",
            priority="LOW",
            category="OUTDOOR_ACTIVITY",
            title="Favorable Air Quality",
            message="Conditions are favorable for normal outdoor activities, physical exercise, and natural ventilation.",
            reason="Current air quality and pollutant concentrations are within clean ambient ranges.",
            icon="🌿"
        )

    # Rule Group B: Particulate Matter (PM2.5 / PM10) Specific Context
    if pm25 is not None and pm25 >= 60.0:
        add_rec(
            rec_id="rec_pm25_indoor",
            priority="HIGH",
            category="EXPOSURE",
            title="Indoor Air Conservation",
            message="Keep windows closed during peak traffic hours and consider utilizing high-efficiency indoor air filters.",
            reason=f"Fine particulate matter (PM2.5: {round(pm25, 1)} µg/m³) is elevated above baseline thresholds.",
            icon="🏠"
        )
    elif pm10 is not None and pm10 >= 100.0:
        add_rec(
            rec_id="rec_pm10_dust",
            priority="MEDIUM",
            category="POLLUTION",
            title="Coarse Dust Precaution",
            message="Be mindful of airborne road dust and industrial particulates; avoid idling in heavy commercial zones.",
            reason=f"Coarse particulate matter (PM10: {round(pm10, 1)} µg/m³) is currently elevated.",
            icon="💨"
        )

    # Rule Group C: ML Forecast & Anticipated Trend
    if pred_trend == "WORSENING" and predicted_aqi and current_aqi and (predicted_aqi > current_aqi + 15):
        add_rec(
            rec_id="rec_forecast_deteriorating",
            priority="HIGH" if risk_level in ("HIGH", "VERY HIGH", "CRITICAL") else "MEDIUM",
            category="TRAVEL",
            title="Anticipate Deteriorating Air Quality",
            message="Plan outdoor trips and commutes in advance, as predictive models forecast deteriorating air quality.",
            reason=f"ML model forecasts AQI to rise to approximately {round(predicted_aqi, 1)} over the next horizon.",
            icon="🔮"
        )
    elif pred_trend == "IMPROVING" and predicted_aqi and current_aqi and (predicted_aqi < current_aqi - 20):
        add_rec(
            rec_id="rec_forecast_clearing",
            priority="LOW",
            category="TRAVEL",
            title="Expected Atmospheric Improvement",
            message="Atmospheric dispersal is expected to improve air quality over the coming forecast interval.",
            reason=f"Predicted AQI trend indicates downward dispersal toward {round(predicted_aqi, 1)}.",
            icon="🌤️"
        )

    # Rule Group D: Anomaly Spikes
    if anomaly_status in ("HIGH ANOMALY", "EXTREME ANOMALY"):
        add_rec(
            rec_id="rec_anomaly_investigation",
            priority="HIGH",
            category="ANOMALY",
            title="Sudden Pollution Surge Detected",
            message="Exercise additional caution regarding sudden localized emissions or episodic particulate spikes.",
            reason=f"A statistical anomaly ({anomaly_status}) indicates sudden divergence from established baseline.",
            icon="⚡"
        )

    # Rule Group E: Hotspot Persistence
    if hotspot_level in ("HOTSPOT", "SEVERE HOTSPOT"):
        add_rec(
            rec_id="rec_hotspot_spatial",
            priority="MEDIUM",
            category="POLLUTION",
            title="Persistent Regional Hotspot",
            message="Pollution levels in this city remain persistently elevated compared to neighboring regional centers.",
            reason=f"Spatial analysis ranks this region as an active {hotspot_level}.",
            icon="📍"
        )

    # Rule Group F: Weather Influence (Wind, Heat, Stagnation)
    if latest_weather:
        wind_speed = latest_weather.wind_speed
        temp = latest_weather.temperature
        humidity = latest_weather.humidity

        if wind_speed is not None and wind_speed < 5.0 and current_aqi and current_aqi > 100:
            add_rec(
                rec_id="rec_weather_stagnation",
                priority="MEDIUM",
                category="WEATHER",
                title="Atmospheric Stagnation Warning",
                message="Very light winds are inhibiting dispersion; pollutants are lingering near ground level.",
                reason=f"Calm wind speed ({wind_speed} km/h) promotes localized pollutant entrapment.",
                icon="🌫️"
            )
        elif temp is not None and temp >= 38.0 and current_aqi and current_aqi > 100:
            add_rec(
                rec_id="rec_heat_pollution_compound",
                priority="HIGH",
                category="WEATHER",
                title="Compounded Heat & Air Stress",
                message="Stay well-hydrated and avoid midday sun; high temperatures and ozone formation compound cardiovascular strain.",
                reason=f"High ambient temperature ({temp}°C) combined with elevated AQI increases heat-pollution stress.",
                icon="☀️"
            )

    # Sort recommendations by priority: HIGH -> MEDIUM -> LOW
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))

    # Keep top 5 to prevent visual clutter and spam
    final_recs = recommendations[:5]

    return {
        "success": True,
        "region": region.name,
        "region_id": region.id,
        "generated_at": now_iso,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "data_available": True,
        "total_recommendations": len(final_recs),
        "recommendations": final_recs
    }
