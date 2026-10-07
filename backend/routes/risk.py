"""
AirGuard AI - Risk Assessment, Recommendations & Alert Routes (Phase 6)
------------------------------------------------------------------------
Endpoints:
- GET  /api/risk/{region_identifier}: Comprehensive explainable environmental risk assessment
- GET  /api/risk: Overview of risk assessments across all active monitored regions
- GET  /api/recommendations/{region_identifier}: Context-aware health and activity advisories
- GET  /api/alerts: System-wide alert center query with optional filters
- GET  /api/alerts/{region_identifier}: Alert history and active warnings for a specific region
- POST /api/alerts/{alert_id}/read: Marks an alert as read
- POST /api/alerts/{alert_id}/acknowledge: Acknowledges an active alert
- POST /api/alerts/{alert_id}/resolve: Resolves an alert
- POST /api/alerts/evaluate/{region_identifier}: Triggers alert evaluation and dispatch on live data
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from database.session import get_db
from backend.services.region_service import get_all_regions, get_region_by_identifier
from backend.services.risk_service import assess_environmental_risk
from backend.services.recommendation_service import generate_recommendations
from backend.services.alert_service import (
    evaluate_and_dispatch_alerts,
    get_alerts_for_region,
    get_all_alerts,
    mark_alert_read,
    acknowledge_alert,
    resolve_alert,
    get_severity_color
)
from backend.models.schemas import (
    RiskAssessmentResponse,
    MultiRegionRiskResponse,
    RecommendationResponse,
    AlertItem,
    AlertListResponse,
    AlertActionResponse,
    ErrorResponse
)
from backend.utils.logger import logger

router = APIRouter(tags=["Risk Assessment, Recommendations & Alerts (Phase 6)"])


# =====================================================================
# 1. RISK ASSESSMENT ENDPOINTS
# =====================================================================

@router.get(
    "/risk/{region_identifier}",
    response_model=RiskAssessmentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Risk assessment computation error"}
    }
)
def get_region_risk(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Computes an explainable, deterministic Composite Environmental Risk Score (0-100)
    for a monitored region based on live AQI, ML forecasts, particulates, hotspots, and anomalies.
    """
    try:
        result = assess_environmental_risk(db, region_identifier)
        return RiskAssessmentResponse(**result)
    except ValueError as ve:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error computing risk for region {region_identifier}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess environmental risk: {str(e)}"
        )


@router.get(
    "/risk",
    response_model=MultiRegionRiskResponse,
    responses={500: {"model": ErrorResponse, "description": "Multi-region risk error"}}
)
def get_all_regions_risk(db: Session = Depends(get_db)):
    """
    Returns environmental risk profiles across all active monitored cities.
    """
    try:
        active_regions = get_all_regions(db, active_only=True)
        region_assessments = []

        for reg in active_regions:
            try:
                assessment = assess_environmental_risk(db, reg.id)
                region_assessments.append(RiskAssessmentResponse(**assessment))
            except Exception as ex:
                logger.warning(f"Could not compute risk for region {reg.name}: {ex}")

        # Sort from highest risk score to lowest
        region_assessments.sort(key=lambda x: x.risk_score, reverse=True)

        return MultiRegionRiskResponse(
            success=True,
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_regions=len(region_assessments),
            regions=region_assessments
        )
    except Exception as e:
        logger.error(f"Error evaluating multi-region risk: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve multi-region risk overview: {str(e)}"
        )


# =====================================================================
# 2. SMART RECOMMENDATION ENDPOINTS
# =====================================================================

@router.get(
    "/recommendations/{region_identifier}",
    response_model=RecommendationResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Recommendation error"}
    }
)
def get_region_recommendations(
    region_identifier: str,
    db: Session = Depends(get_db)
):
    """
    Generates context-aware, prioritized, and non-diagnostic health and activity
    recommendations based on actual real-time environmental metrics.
    """
    try:
        result = generate_recommendations(db, region_identifier)
        return RecommendationResponse(**result)
    except ValueError as ve:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error generating recommendations for {region_identifier}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


# =====================================================================
# 3. INTELLIGENT ALERT ENDPOINTS
# =====================================================================

def _format_alert_item(alert) -> AlertItem:
    return AlertItem(
        id=alert.id,
        region_id=alert.region_id,
        region=alert.region.name if alert.region else None,
        timestamp=alert.timestamp.isoformat() if alert.timestamp else "",
        created_at=alert.created_at.isoformat() if alert.created_at else (alert.timestamp.isoformat() if alert.timestamp else ""),
        trigger_type=alert.alert_type,
        alert_type=alert.alert_type,
        title=alert.title or alert.alert_type.replace("_", " ").title(),
        message=alert.message,
        severity=alert.severity,
        severity_color=get_severity_color(alert.severity),
        status=alert.status,
        read_at=alert.read_at.isoformat() if alert.read_at else None,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        dedupe_key=alert.dedupe_key
    )


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    responses={500: {"model": ErrorResponse, "description": "Alert query error"}}
)
def get_alerts(
    region: Optional[str] = Query(None, description="Optional region name or ID to filter by"),
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, LOW, MEDIUM, HIGH, CRITICAL"),
    alert_status: Optional[str] = Query(None, alias="status", description="Filter by status: UNREAD, READ, ACKNOWLEDGED, RESOLVED"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts to return"),
    db: Session = Depends(get_db)
):
    """
    Returns alerts across the platform with optional filters for region, severity, and status.
    """
    try:
        if region:
            reg_obj = get_region_by_identifier(db, region)
            if not reg_obj:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Region '{region}' not found."
                )
            # Automatically evaluate alerts on fetch to keep warnings fresh
            evaluate_and_dispatch_alerts(db, reg_obj.id)
            alerts = get_alerts_for_region(db, reg_obj.id, status=alert_status, limit=limit)
            region_name = reg_obj.name
        else:
            alerts = get_all_alerts(db, severity=severity, status=alert_status, limit=limit)
            region_name = None

        alert_items = [_format_alert_item(a) for a in alerts]
        unread_count = sum(1 for a in alert_items if a.status == "UNREAD")

        return AlertListResponse(
            success=True,
            total_alerts=len(alert_items),
            unread_count=unread_count,
            region=region_name,
            alerts=alert_items
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query alerts: {str(e)}"
        )


@router.get(
    "/alerts/{region_identifier}",
    response_model=AlertListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Region not found"},
        500: {"model": ErrorResponse, "description": "Alert retrieval error"}
    }
)
def get_region_alerts(
    region_identifier: str,
    alert_status: Optional[str] = Query(None, alias="status", description="Filter by status: UNREAD, READ, ACKNOWLEDGED, RESOLVED"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Returns historical and active alerts for a specific region.
    Evaluates real telemetry against alert conditions with cooldown deduplication.
    """
    try:
        reg_obj = get_region_by_identifier(db, region_identifier)
        if not reg_obj:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Region '{region_identifier}' not found."
            )

        # Trigger data-driven evaluation
        evaluate_and_dispatch_alerts(db, reg_obj.id)

        alerts = get_alerts_for_region(db, reg_obj.id, status=alert_status, limit=limit)
        alert_items = [_format_alert_item(a) for a in alerts]
        unread_count = sum(1 for a in alert_items if a.status == "UNREAD")

        return AlertListResponse(
            success=True,
            total_alerts=len(alert_items),
            unread_count=unread_count,
            region=reg_obj.name,
            alerts=alert_items
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving alerts for region {region_identifier}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve region alerts: {str(e)}"
        )


@router.post(
    "/alerts/{alert_id}/read",
    response_model=AlertActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Action error"}
    }
)
def set_alert_read(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Marks an alert as READ.
    """
    try:
        updated = mark_alert_read(db, alert_id)
        if not updated:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Alert with ID {alert_id} not found."
            )
        return AlertActionResponse(
            success=True,
            message="Alert marked as READ.",
            alert=_format_alert_item(updated)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking alert {alert_id} as read: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert status: {str(e)}"
        )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Action error"}
    }
)
def set_alert_acknowledged(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Marks an active alert as ACKNOWLEDGED.
    """
    try:
        updated = acknowledge_alert(db, alert_id)
        if not updated:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Alert with ID {alert_id} not found."
            )
        return AlertActionResponse(
            success=True,
            message="Alert acknowledged.",
            alert=_format_alert_item(updated)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=AlertActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Action error"}
    }
)
def set_alert_resolved(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Marks an active alert as RESOLVED.
    """
    try:
        updated = resolve_alert(db, alert_id)
        if not updated:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Alert with ID {alert_id} not found."
            )
        return AlertActionResponse(
            success=True,
            message="Alert resolved.",
            alert=_format_alert_item(updated)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )
