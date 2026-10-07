"""
AirGuard AI - Intelligent Alert Service (Phase 6)
-------------------------------------------------
Evaluates actual environmental telemetry, ML forecasts, hotspot classifications,
and statistical anomalies to trigger, persist, and manage environmental alerts.

Key Features:
- Strict Data-Driven Triggers (no synthetic or fabricated alerts)
- Deduplication & Cooldown (prevents repetitive alert spam on frontend refresh)
- Severity Escalation (allows critical updates to bypass cooldown if condition worsens)
- Full Alert Lifecycle Tracking (UNREAD -> READ -> ACKNOWLEDGED -> RESOLVED)
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from config.settings import settings
from backend.models.models import Region, Alert, AirQualityObservation, utc_now
from backend.services.region_service import get_region_by_identifier
from backend.services.risk_service import assess_environmental_risk
from backend.services.hotspot_service import get_regional_hotspot_detail
from backend.services.anomaly_service import detect_anomalies_for_region
from backend.services.prediction_service import get_prediction_for_region
from backend.utils.logger import logger


SEVERITY_LEVELS = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4
}

SEVERITY_COLORS = {
    "CRITICAL": "#7f1d1d",
    "HIGH": "#ea580c",
    "MEDIUM": "#f59e0b",
    "LOW": "#10b981",
    "INFO": "#3b82f6"
}


def get_severity_rank(severity: str) -> int:
    return SEVERITY_LEVELS.get(severity.upper(), 0)


def get_severity_color(severity: str) -> str:
    return SEVERITY_COLORS.get(severity.upper(), "#6b7280")


def evaluate_and_dispatch_alerts(
    db: Session,
    region_identifier: Any
) -> List[Alert]:
    """
    Evaluates real atmospheric data for the specified region, creates alerts
    for active hazard conditions, and applies strict deduplication and cooldown.
    Returns newly created alerts in this evaluation.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise ValueError(f"Region '{region_identifier}' not found.")

    logger.info(f"Evaluating alert triggers for region '{region.name}' (ID: {region.id})")

    # 1. Fetch risk assessment
    risk_info = assess_environmental_risk(db, region.id)
    if not risk_info.get("data_available", False):
        logger.debug(f"Insufficient data to trigger alerts for {region.name}.")
        return []

    risk_score = risk_info.get("risk_score", 0.0)
    risk_level = risk_info.get("risk_level", "LOW")

    # 2. Fetch latest telemetry
    latest_aq = (
        db.query(AirQualityObservation)
        .filter(AirQualityObservation.region_id == region.id)
        .order_by(AirQualityObservation.timestamp.desc())
        .first()
    )
    current_aqi = latest_aq.aqi if latest_aq else None
    pm25 = latest_aq.pm2_5 if latest_aq else None

    # 3. Fetch prediction
    pred_res = get_prediction_for_region(region.id, db)
    pred_data = pred_res.get("prediction") if pred_res.get("status") == "available" else None
    pred_trend = pred_data.get("trend") if pred_data else None
    predicted_aqi = pred_data.get("predicted_aqi") if pred_data else None

    # 4. Fetch hotspot & anomaly
    hotspot_detail = get_regional_hotspot_detail(db, region.id)
    hotspot_level = hotspot_detail.get("level", "NORMAL") if hotspot_detail else "NORMAL"

    anomaly_res = detect_anomalies_for_region(db, region.id, persist=False)
    anomaly_status = anomaly_res.get("anomaly_status", "NORMAL")
    anomalies_list = anomaly_res.get("anomalies", [])

    candidate_alerts: List[Dict[str, Any]] = []

    # TRIGGER 1: Critical or High Risk
    if settings.HIGH_RISK_ALERT_ENABLED:
        if risk_level == "CRITICAL":
            candidate_alerts.append({
                "trigger_type": "CRITICAL_RISK",
                "severity": "CRITICAL",
                "title": "Critical Environmental Risk",
                "message": f"Region {region.name} has entered Critical Environmental Risk (Score: {risk_score}/100). Severe exposure hazard present."
            })
        elif risk_level in ("HIGH", "VERY HIGH"):
            candidate_alerts.append({
                "trigger_type": "HIGH_RISK",
                "severity": "HIGH",
                "title": "High Environmental Risk",
                "message": f"Region {region.name} is experiencing {risk_level} Environmental Risk (Score: {risk_score}/100). Sensitive groups and outdoors should exercise high caution."
            })

    # TRIGGER 2: Pollution Anomaly Spike
    if settings.ANOMALY_ALERT_ENABLED and anomaly_status in ("HIGH ANOMALY", "EXTREME ANOMALY"):
        top_anomaly_desc = ""
        if anomalies_list:
            top_metric = anomalies_list[0].get("metric", "Pollutant")
            obs = anomalies_list[0].get("observed_value")
            top_anomaly_desc = f" ({top_metric}: {round(obs, 1)} µg/m³)"
        
        severity = "CRITICAL" if anomaly_status == "EXTREME ANOMALY" else "HIGH"
        candidate_alerts.append({
            "trigger_type": "POLLUTION_ANOMALY",
            "severity": severity,
            "title": "Unusual Pollution Anomaly Surge",
            "message": f"Sudden statistical departure detected in {region.name}{top_anomaly_desc}. Readings diverge significantly from the historical baseline."
        })

    # TRIGGER 3: Pollution Hotspot Classification
    if settings.HOTSPOT_ALERT_ENABLED and hotspot_level in ("HOTSPOT", "SEVERE HOTSPOT"):
        severity = "HIGH" if hotspot_level == "SEVERE HOTSPOT" else "MEDIUM"
        candidate_alerts.append({
            "trigger_type": "HOTSPOT_DETECTED",
            "severity": severity,
            "title": f"Active Pollution Hotspot ({hotspot_level})",
            "message": f"{region.name} is classified as an active pollution hotspot with composite score {hotspot_detail.get('hotspot_score')}."
        })

    # TRIGGER 4: Predicted AQI Deterioration
    if settings.PREDICTION_ALERT_ENABLED and pred_trend == "WORSENING" and predicted_aqi and current_aqi:
        if predicted_aqi >= 150.0 and (predicted_aqi - current_aqi >= 20.0):
            candidate_alerts.append({
                "trigger_type": "PREDICTED_DETERIORATION",
                "severity": "MEDIUM",
                "title": "Forecasted Air Quality Deterioration",
                "message": f"Predictive models forecast AQI worsening from {round(current_aqi)} to {round(predicted_aqi, 1)} in the next interval."
            })

    # TRIGGER 5: Extreme Particulate Spike
    if pm25 is not None and pm25 >= 120.0:
        candidate_alerts.append({
            "trigger_type": "POLLUTANT_THRESHOLD",
            "severity": "HIGH",
            "title": "Severe PM2.5 Particulate Concentration",
            "message": f"Hazardous fine particulate concentration detected: PM2.5 is {round(pm25, 1)} µg/m³."
        })

    # Deduplicate and Dispatch candidates
    created_alerts: List[Alert] = []
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)

    for cand in candidate_alerts:
        trigger_type = cand["trigger_type"]
        cand_severity = cand["severity"]
        dedupe_key = f"{region.id}_{trigger_type}"

        if settings.ALERT_DEDUPLICATION_ENABLED:
            # Query most recent alert with same dedupe_key
            recent_alert = (
                db.query(Alert)
                .filter(
                    Alert.region_id == region.id,
                    Alert.dedupe_key == dedupe_key
                )
                .order_by(desc(Alert.timestamp))
                .first()
            )

            if recent_alert:
                recent_ts = recent_alert.timestamp
                if recent_ts.tzinfo is None:
                    recent_ts = recent_ts.replace(tzinfo=timezone.utc)

                within_cooldown = recent_ts >= cooldown_cutoff

                if within_cooldown:
                    # Escalation check: if candidate severity is strictly higher, allow escalation alert!
                    curr_rank = get_severity_rank(cand_severity)
                    prev_rank = get_severity_rank(recent_alert.severity)

                    if curr_rank <= prev_rank:
                        logger.debug(
                            f"Suppressed duplicate alert for {region.name} (trigger: {trigger_type}, "
                            f"severity: {cand_severity}). Active alert #{recent_alert.id} in cooldown."
                        )
                        continue
                    else:
                        logger.info(
                            f"Escalation detected for {region.name} ({recent_alert.severity} -> {cand_severity}). "
                            f"Bypassing cooldown to dispatch critical update."
                        )

        # Create and persist new alert
        new_alert = Alert(
            region_id=region.id,
            timestamp=utc_now(),
            alert_type=trigger_type,
            title=cand["title"],
            message=cand["message"],
            severity=cand_severity,
            status="UNREAD",
            created_at=utc_now(),
            dedupe_key=dedupe_key,
            expires_at=utc_now() + timedelta(hours=24)
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        created_alerts.append(new_alert)
        logger.info(f"Dispatched new alert #{new_alert.id} [{cand_severity}] for {region.name}: {cand['title']}")

    return created_alerts


def get_alerts_for_region(
    db: Session,
    region_identifier: Any,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Alert]:
    """Retrieves alerts for a specific region, ordered from newest to oldest."""
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise ValueError(f"Region '{region_identifier}' not found.")

    query = db.query(Alert).filter(Alert.region_id == region.id)
    if status:
        query = query.filter(Alert.status == status.upper())

    return query.order_by(desc(Alert.timestamp)).limit(limit).all()


def get_all_alerts(
    db: Session,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Alert]:
    """Retrieves all alerts across all monitored regions with optional filters."""
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status:
        query = query.filter(Alert.status == status.upper())

    return query.order_by(desc(Alert.timestamp)).limit(limit).all()


def mark_alert_read(db: Session, alert_id: int) -> Optional[Alert]:
    """Marks an alert as READ."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None

    if alert.status == "UNREAD":
        alert.status = "READ"
        alert.read_at = utc_now()
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert #{alert_id} marked as READ.")
    return alert


def acknowledge_alert(db: Session, alert_id: int) -> Optional[Alert]:
    """Marks an alert as ACKNOWLEDGED."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = utc_now()
    if not alert.read_at:
        alert.read_at = utc_now()
    db.commit()
    db.refresh(alert)
    logger.info(f"Alert #{alert_id} marked as ACKNOWLEDGED.")
    return alert


def resolve_alert(db: Session, alert_id: int) -> Optional[Alert]:
    """Marks an alert as RESOLVED."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None

    alert.status = "RESOLVED"
    db.commit()
    db.refresh(alert)
    logger.info(f"Alert #{alert_id} marked as RESOLVED.")
    return alert
