"""
AirGuard AI - Interactive Map Data & Unified Intelligence Dashboard Routes (Phase 7)
-------------------------------------------------------------------------------------
Endpoints:
- GET /api/map-data: Multi-region spatial telemetry, AQI, risk, hotspot, and anomaly markers
- GET /api/dashboard/{region_identifier}: Aggregated single-city intelligence payload
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.session import get_db
from backend.models.models import Region, AirQualityObservation, WeatherObservation, Alert
from backend.services.region_service import get_all_regions, get_region_by_identifier
from backend.services.hotspot_service import assess_hotspots, get_regional_hotspot_detail
from backend.services.anomaly_service import detect_anomalies_for_region
from backend.services.risk_service import assess_environmental_risk
from backend.services.recommendation_service import generate_recommendations
from backend.services.alert_service import get_alerts_for_region, get_severity_color
from backend.services.prediction_service import get_prediction_for_region
from backend.models.schemas import (
    MapDataResponse,
    MapRegionItem,
    DashboardAggregatedResponse,
    ErrorResponse
)
from backend.utils.logger import logger

router = APIRouter(tags=["Map & Dashboard Intelligence (Phase 7)"])


def _classify_aqi(aqi: Optional[float]) -> Tuple[str, str]:
    """
    Standard AQI category and theme color classifier.
    Matches the existing frontend and environmental standard.
    """
    if aqi is None:
        return "Unknown", "#6b7280"
    try:
        val = float(aqi)
    except (ValueError, TypeError):
        return "Unknown", "#6b7280"

    if val <= 50:
        return "Good", "#10b981"
    elif val <= 100:
        return "Moderate", "#f59e0b"
    elif val <= 150:
        return "Unhealthy for Sensitive Groups", "#f97316"
    elif val <= 200:
        return "Unhealthy", "#ef4444"
    elif val <= 300:
        return "Very Unhealthy", "#8b5cf6"
    else:
        return "Hazardous", "#7f1d1d"


@router.get(
    "/map-data",
    response_model=MapDataResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Failed to aggregate map data"}
    }
)
def get_map_data(db: Session = Depends(get_db)):
    """
    Returns aggregated spatial data for all active monitored regions to power
    the interactive pollution map. Each region contains coordinates, latest AQI,
    risk level, hotspot status, anomaly indicators, and active alert counters.
    Zero fabricated data; missing points are represented cleanly with nulls.
    """
    try:
        regions = db.query(Region).filter(Region.is_active == True).all()
        now_iso = datetime.now(timezone.utc).isoformat()

        if not regions:
            return MapDataResponse(
                success=True,
                timestamp=now_iso,
                total_regions=0,
                regions=[]
            )

        # 1. Hotspot assessment across all regions in a single pass
        hotspot_batch = assess_hotspots(db, persist=False)
        hotspot_map: Dict[int, Dict[str, Any]] = {
            h["region_id"]: h for h in hotspot_batch.get("hotspots", [])
        }

        region_items: List[MapRegionItem] = []

        for r in regions:
            # Latest real air quality observation
            latest_aq = (
                db.query(AirQualityObservation)
                .filter(AirQualityObservation.region_id == r.id)
                .order_by(desc(AirQualityObservation.timestamp))
                .first()
            )

            aqi_val = latest_aq.aqi if latest_aq else None
            aqi_cat, aqi_col = _classify_aqi(aqi_val)

            # Hotspot data
            h_info = hotspot_map.get(r.id, {})
            is_hotspot = bool(h_info.get("is_hotspot", False))
            hotspot_score = h_info.get("hotspot_score")
            hotspot_severity = h_info.get("level")

            # Risk assessment
            risk_info = assess_environmental_risk(db, r.id)
            risk_score = risk_info.get("risk_score")
            risk_level = risk_info.get("risk_level")
            risk_color = risk_info.get("risk_color")

            # Anomaly assessment (fast non-persisting 24h scan)
            anom_info = detect_anomalies_for_region(db, r.id, hours=24, persist=False)
            has_anomaly = bool(anom_info.get("has_anomalies", False))
            anomalies_list = anom_info.get("anomalies", [])
            latest_anomaly_metric = anomalies_list[0].get("metric") if anomalies_list else None
            anomaly_severity = anomalies_list[0].get("severity") if anomalies_list else None

            # Active/unread alert count
            active_alerts = (
                db.query(Alert)
                .filter(
                    Alert.region_id == r.id,
                    Alert.status.in_(["UNREAD", "READ", "ACKNOWLEDGED"])
                )
                .count()
            )

            ts_str = latest_aq.timestamp.isoformat() if latest_aq and latest_aq.timestamp else None

            item = MapRegionItem(
                region_id=r.id,
                region=r.name,
                latitude=r.latitude,
                longitude=r.longitude,
                state=r.state,
                country=r.country,
                aqi=aqi_val,
                aqi_category=aqi_cat,
                aqi_color=aqi_col,
                pm25=latest_aq.pm2_5 if latest_aq else None,
                pm10=latest_aq.pm10 if latest_aq else None,
                risk_score=risk_score,
                risk_level=risk_level,
                risk_color=risk_color,
                is_hotspot=is_hotspot,
                hotspot_score=hotspot_score,
                hotspot_severity=hotspot_severity,
                has_anomaly=has_anomaly,
                latest_anomaly_metric=latest_anomaly_metric,
                anomaly_severity=anomaly_severity,
                active_alerts_count=active_alerts,
                source=latest_aq.source if latest_aq else None,
                timestamp=ts_str,
                updated_at=ts_str
            )
            region_items.append(item)

        return MapDataResponse(
            success=True,
            timestamp=now_iso,
            total_regions=len(region_items),
            regions=region_items
        )

    except Exception as e:
        logger.error(f"Error compiling map-data: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to aggregate environmental map telemetry: {str(e)}"
        )


@router.get(
    "/dashboard/{region_identifier}",
    response_model=DashboardAggregatedResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Failed to assemble dashboard intelligence"}
    }
)
def get_dashboard_summary(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the complete environmental intelligence bundle for a single user-selected region.
    Integrates real-time observations, forecast, hotspot, anomaly, risk, recommendations,
    and active alerts in a single consolidated response.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Latest Air Quality Observation
        latest_aq = (
            db.query(AirQualityObservation)
            .filter(AirQualityObservation.region_id == region.id)
            .order_by(desc(AirQualityObservation.timestamp))
            .first()
        )
        aq_payload = None
        if latest_aq:
            aq_cat, aq_col = _classify_aqi(latest_aq.aqi)
            aq_payload = {
                "region": region.name,
                "region_id": region.id,
                "timestamp": latest_aq.timestamp.isoformat() if latest_aq.timestamp else None,
                "aqi": latest_aq.aqi,
                "category": aq_cat,
                "category_color": aq_col,
                "pm25": latest_aq.pm2_5,
                "pm10": latest_aq.pm10,
                "co": latest_aq.co,
                "no2": latest_aq.no2,
                "so2": latest_aq.so2,
                "o3": latest_aq.o3,
                "source": latest_aq.source
            }

        # 2. Latest Weather Observation
        latest_weather = (
            db.query(WeatherObservation)
            .filter(WeatherObservation.region_id == region.id)
            .order_by(desc(WeatherObservation.timestamp))
            .first()
        )
        weather_payload = None
        if latest_weather:
            weather_payload = {
                "region": region.name,
                "region_id": region.id,
                "timestamp": latest_weather.timestamp.isoformat() if latest_weather.timestamp else None,
                "temperature": latest_weather.temperature,
                "humidity": latest_weather.humidity,
                "wind_speed": latest_weather.wind_speed,
                "wind_direction": latest_weather.wind_direction,
                "pressure": latest_weather.pressure,
                "rainfall": latest_weather.rainfall,
                "source": latest_weather.source
            }

        # 3. ML Prediction (Phase 4)
        pred_result = get_prediction_for_region(region.id, db)

        # 4. Hotspot Analysis (Phase 5)
        hotspot_result = get_regional_hotspot_detail(db, region.id)

        # 5. Anomaly Detection (Phase 5)
        anomaly_result = detect_anomalies_for_region(db, region.id, hours=24, persist=False)

        # 6. Environmental Risk Assessment (Phase 6)
        risk_result = assess_environmental_risk(db, region.id)

        # 7. Smart Recommendations (Phase 6)
        recs_dict = generate_recommendations(db, region.id)
        recs_list = recs_dict.get("recommendations", [])

        # 8. Region Alerts (Phase 6)
        alerts_models = get_alerts_for_region(db, region.id, limit=20)
        alerts_list = []
        unread_count = 0
        for a in alerts_models:
            if a.status == "UNREAD":
                unread_count += 1
            alerts_list.append({
                "id": a.id,
                "region_id": a.region_id,
                "region": region.name,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "trigger_type": a.alert_type,
                "alert_type": a.alert_type,
                "title": a.title,
                "message": a.message,
                "severity": a.severity,
                "severity_color": get_severity_color(a.severity),
                "status": a.status,
                "read_at": a.read_at.isoformat() if a.read_at else None,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None
            })

        return DashboardAggregatedResponse(
            success=True,
            region=region.name,
            region_id=region.id,
            latitude=region.latitude,
            longitude=region.longitude,
            state=region.state,
            timestamp=now_iso,
            air_quality=aq_payload,
            weather=weather_payload,
            prediction=pred_result,
            hotspot=hotspot_result,
            anomaly=anomaly_result,
            risk=risk_result,
            recommendations=recs_list,
            alerts=alerts_list,
            unread_alerts_count=unread_count
        )

    except Exception as e:
        logger.error(f"Error assembling dashboard intelligence for region {region.name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to assemble dashboard intelligence: {str(e)}"
        )
