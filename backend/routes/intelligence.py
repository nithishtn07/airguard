"""
AirGuard AI - Environmental Intelligence Routes (Phase 5)
--------------------------------------------------------
Endpoints:
- GET /api/hotspots: Multi-region pollution hotspot detection and dynamic ranking
- GET /api/hotspots/{region_identifier}: In-depth hotspot assessment for a single region
- GET /api/anomalies/{region_identifier}: Statistical anomaly detection and timeline for a region
- GET /api/anomalies: Multi-region overview or specific region query
- GET /api/environmental-intelligence/{region_identifier}: Unified spatial-temporal-predictive intelligence
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from backend.services.region_service import get_region_by_identifier
from backend.services.hotspot_service import (
    assess_hotspots,
    get_regional_hotspot_detail
)
from backend.services.anomaly_service import (
    detect_anomalies_for_region,
    assess_all_anomalies
)
from backend.services.prediction_service import get_prediction_for_region
from backend.models.schemas import (
    HotspotResponse,
    HotspotRegionItem,
    AnomalyResponse,
    CombinedIntelligenceResponse,
    ErrorResponse
)
from backend.utils.logger import logger

router = APIRouter(tags=["Environmental Intelligence (Hotspots & Anomalies)"])


def _parse_range_hours(range_param: Optional[str]) -> int:
    """Parses range strings like '24h', '48h', '7d' into integer hours."""
    if not range_param:
        return 24
    rp = range_param.strip().lower()
    if rp.endswith("d"):
        try:
            return int(rp[:-1]) * 24
        except ValueError:
            return 24
    elif rp.endswith("h"):
        try:
            return int(rp[:-1])
        except ValueError:
            return 24
    try:
        return int(rp)
    except ValueError:
        return 24


@router.get(
    "/hotspots",
    response_model=HotspotResponse,
    responses={500: {"model": ErrorResponse, "description": "Hotspot assessment error"}}
)
def get_pollution_hotspots(
    range: str = Query("24h", description="Historical analysis window (e.g. '24h', '48h', '7d')"),
    db: Session = Depends(get_db)
):
    """
    Evaluates and ranks all active monitored regions to identify pollution hotspots.
    Applies multi-factor explainable scoring: AQI severity, relative deviation,
    historical deviation, and persistence.
    """
    try:
        hours = _parse_range_hours(range)
        result = assess_hotspots(db=db, hours=hours, persist=True)
        return HotspotResponse(**result)
    except Exception as e:
        logger.error(f"Error computing pollution hotspots: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess pollution hotspots: {str(e)}"
        )


@router.get(
    "/hotspots/{region_identifier}",
    response_model=HotspotRegionItem,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Hotspot assessment error"}
    }
)
def get_region_hotspot(
    region_identifier: str,
    range: str = Query("24h", description="Historical analysis window"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the detailed hotspot profile for a specific region.
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        hours = _parse_range_hours(range)
        detail = get_regional_hotspot_detail(db, region.id, hours=hours)
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hotspot detail unavailable for region '{region.name}'."
            )
        return HotspotRegionItem(**detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching hotspot for {region_identifier}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate hotspot for region: {str(e)}"
        )


@router.get(
    "/anomalies/{region_identifier}",
    response_model=AnomalyResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Anomaly detection error"}
    }
)
def get_region_anomalies(
    region_identifier: str,
    hours: Optional[int] = Query(None, description="Analysis window in hours"),
    z_threshold: Optional[float] = Query(None, description="Statistical Z-score sensitivity threshold"),
    db: Session = Depends(get_db)
):
    """
    Executes statistical anomaly detection on recent atmospheric telemetry for a specific region.
    Uses causal zero-leakage rolling baselines across priority pollutants (AQI, PM2.5, PM10).
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        result = detect_anomalies_for_region(
            db=db,
            region_identifier=region.id,
            hours=hours,
            z_threshold=z_threshold,
            persist=True
        )
        return AnomalyResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error detecting anomalies for {region_identifier}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute anomaly detection: {str(e)}"
        )


@router.get("/anomalies")
def get_anomalies_overview(
    region: Optional[str] = Query(None, description="Optional region name/identifier filter"),
    hours: Optional[int] = Query(None, description="Analysis window in hours"),
    z_threshold: Optional[float] = Query(None, description="Statistical Z-score threshold"),
    db: Session = Depends(get_db)
):
    """
    Retrieves pollution anomaly detections. If a region is specified, returns single-region analysis;
    otherwise evaluates and summarizes across all active monitored cities.
    """
    try:
        if region:
            reg = get_region_by_identifier(db, region)
            if not reg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Region '{region}' not found."
                )
            result = detect_anomalies_for_region(
                db=db,
                region_identifier=reg.id,
                hours=hours,
                z_threshold=z_threshold,
                persist=True
            )
            return AnomalyResponse(**result)
        else:
            return assess_all_anomalies(db=db, hours=hours, z_threshold=z_threshold)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching anomalies overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess anomalies: {str(e)}"
        )


@router.get(
    "/environmental-intelligence/{region_identifier}",
    response_model=CombinedIntelligenceResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Intelligence aggregation error"}
    }
)
def get_combined_environmental_intelligence(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Unified Environmental Intelligence Endpoint (Phase 5).
    Combines:
    1. Real-time atmospheric conditions (Phase 2)
    2. ML-based AQI prediction & forecast trend (Phase 4)
    3. Multi-factor Hotspot status & ranking (Phase 5 Part A)
    4. Statistical Anomaly status & detected deviations (Phase 5 Part B)
    """
    region = get_region_by_identifier(db, region_identifier)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region '{region_identifier}' not found."
        )

    try:
        # 1. Hotspot assessment
        hotspot_detail = get_regional_hotspot_detail(db, region.id)

        # 2. Anomaly assessment
        anomaly_res = detect_anomalies_for_region(db, region.id, persist=False)

        # 3. Prediction service
        pred_res = get_prediction_for_region(region.id, db)
        pred_data = pred_res.get("prediction") if pred_res.get("status") == "available" else None

        # 4. Current atmospheric data
        current_data = {
            "aqi": hotspot_detail.get("current_aqi") if hotspot_detail else None,
            "pm25": hotspot_detail.get("pm25") if hotspot_detail else None,
            "pm10": hotspot_detail.get("pm10") if hotspot_detail else None
        }

        # 5. Natural language synthesis summary
        hotspot_level = hotspot_detail.get("level", "NORMAL") if hotspot_detail else "NORMAL"
        anomaly_status = anomaly_res.get("anomaly_status", "NORMAL")
        current_aqi_val = current_data.get("aqi", "N/A")
        
        summary_parts = [
            f"Region {region.name}: Current AQI is {current_aqi_val}."
        ]
        
        if hotspot_level in ("HOTSPOT", "SEVERE HOTSPOT"):
            summary_parts.append(
                f"Flagged as a {hotspot_level} (Rank #{hotspot_detail.get('rank', '-')} with composite score {hotspot_detail.get('hotspot_score')})."
            )
        else:
            summary_parts.append(f"Hotspot status is {hotspot_level}.")

        if anomaly_status in ("HIGH ANOMALY", "EXTREME ANOMALY"):
            summary_parts.append(
                f"Active {anomaly_status} detected across recent atmospheric telemetry."
            )
        elif anomaly_status == "UNUSUAL":
            summary_parts.append("Atmospheric readings show unusual divergence from historical baseline.")
        else:
            summary_parts.append("No statistical anomalies detected; readings match historical pattern.")

        if pred_data:
            summary_parts.append(
                f"Next horizon forecasted AQI: {round(pred_data.get('predicted_aqi', 0), 1)} ({pred_data.get('trend')} trend)."
            )

        summary_text = " ".join(summary_parts)

        return CombinedIntelligenceResponse(
            success=True,
            region=region.name,
            region_id=region.id,
            coordinates={
                "latitude": region.latitude,
                "longitude": region.longitude
            },
            generated_at=anomaly_res.get("generated_at", ""),
            current=current_data,
            prediction=pred_data,
            hotspot=hotspot_detail or {},
            anomaly={
                "status": anomaly_status,
                "highest_score": anomaly_res.get("highest_anomaly_score", 0.0),
                "anomalies_count": len(anomaly_res.get("anomalies", [])),
                "anomalies": anomaly_res.get("anomalies", [])
            },
            summary=summary_text
        )

    except Exception as e:
        logger.error(f"Error compiling combined intelligence for {region.name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile combined environmental intelligence: {str(e)}"
        )
