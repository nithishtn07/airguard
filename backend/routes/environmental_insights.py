"""
AirGuard AI - Environmental Insights Routes
Phase 9: API endpoints for:
1. Location search / Geocoding (/api/location/search)
2. Location reverse geocoding (/api/location/reverse)
3. Custom period environmental analysis (/api/environmental-insights/analysis)
4. Public environmental & compliance records (/api/environmental-records)
5. Condition-relevant best practices (/api/best-practices)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from backend.services.geocoding_service import geocoding_service
from backend.services.environmental_information_service import environmental_information_service
from backend.services.best_practices_service import best_practices_service
from backend.services.insights_analysis_service import insights_analysis_service
from backend.services.region_service import get_region_by_name
from backend.utils.logger import logger

router = APIRouter(tags=["Environmental Insights & Phase 9"])


@router.get("/location/search")
def search_location(
    q: str = Query(..., description="Query string (city, district, locality, state)"),
    limit: int = Query(default=5, ge=1, le=15, description="Maximum number of candidates"),
):
    """
    Geocodes a search string into geographic coordinates and structured location metadata.
    Cross-references against default system regions.
    """
    cleaned_q = q.strip()
    if not cleaned_q or len(cleaned_q) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must contain at least 2 characters.",
        )

    try:
        results = geocoding_service.search_locations(query=cleaned_q, limit=limit)
        return {
            "success": True,
            "query": cleaned_q,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error executing location search for '{cleaned_q}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding service encountered an unexpected error.",
        )


@router.get("/location/reverse")
def reverse_geocode_location(
    lat: float = Query(..., description="Latitude coordinate (-90 to +90)"),
    lon: float = Query(..., description="Longitude coordinate (-180 to +180)"),
):
    """
    Performs reverse geocoding from map coordinates to structured locality details.
    """
    if lat < -90.0 or lat > 90.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude must be between -90.0 and 90.0.",
        )
    if lon < -180.0 or lon > 180.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Longitude must be between -180.0 and 180.0.",
        )

    try:
        loc = geocoding_service.reverse_geocode(lat=lat, lon=lon)
        return {
            "success": True,
            "location": loc,
        }
    except Exception as e:
        logger.error(f"Error reverse geocoding ({lat}, {lon}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reverse geocoding service encountered an error.",
        )


@router.get("/environmental-insights/analysis")
def analyze_environmental_window(
    lat: float = Query(..., description="Location latitude"),
    lon: float = Query(..., description="Location longitude"),
    name: Optional[str] = Query(None, description="Location name"),
    display_name: Optional[str] = Query(None, description="Formatted location label"),
    state: Optional[str] = Query(None, description="State / Province"),
    country: Optional[str] = Query("India", description="Country"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Executes custom time-window historical air quality analysis for arbitrary locations.
    Calculates coverage, mathematical statistics, transparent trend direction,
    weather correlations, ML predictions (where supported), and public compliance records.
    """
    # Check if this matches one of our seeded regions
    matched_id = None
    if name:
        r = get_region_by_name(db, name)
        if r:
            matched_id = r.id

    location_payload = {
        "name": name or "Selected Coordinate",
        "display_name": display_name or (f"{name}, {state}, {country}" if name else f"{lat:.4f}, {lon:.4f}"),
        "latitude": lat,
        "longitude": lon,
        "state": state,
        "country": country,
        "matched_region_id": matched_id,
    }

    try:
        analysis_result = insights_analysis_service.analyze_location_window(
            db=db,
            location=location_payload,
            start_date=start_date,
            end_date=end_date,
        )

        if not analysis_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=analysis_result.get("error", "Analysis request could not be processed."),
            )

        return analysis_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in environmental analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while compiling environmental insights.",
        )


@router.get("/environmental-records")
def get_environmental_records(
    location: Optional[str] = Query(None, description="Location name"),
    state: Optional[str] = Query(None, description="State"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    category: Optional[str] = Query(None, description="Record category"),
):
    """
    Queries legitimate, public environmental notices, directives, and action plans
    from verified regulatory authorities (CPCB, PRANA, State PCBs).
    """
    records = environmental_information_service.get_records(
        location_name=location,
        state=state,
        latitude=lat,
        longitude=lon,
        start_date=start_date,
        end_date=end_date,
        category=category,
    )
    return {
        "success": True,
        "data": records,
    }


@router.get("/best-practices")
def get_best_practices(
    aqi: Optional[float] = Query(None, description="Current or average AQI"),
    pm25: Optional[float] = Query(None, description="PM2.5 concentration"),
    pm10: Optional[float] = Query(None, description="PM10 concentration"),
    location: Optional[str] = Query(None, description="Location context"),
):
    """
    Generates structured best practices partitioned into:
    A. Personal Exposure Reduction
    B. Community-Level Practices
    C. Local Air-Quality Improvement
    Conditioned dynamically on observed pollution levels.
    """
    practices = best_practices_service.generate_best_practices(
        aqi=aqi,
        pm25=pm25,
        pm10=pm10,
        location_name=location,
    )
    return {
        "success": True,
        "data": practices,
    }
