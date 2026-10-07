"""
AirGuard AI - Pollution Hotspot Detection Service (Phase 5)
----------------------------------------------------------
Identifies regions/locations with persistently or currently elevated pollution
relative to other monitored regions and their own historical baselines.
Transparent, explainable, multi-factor scoring mechanism with zero fabricated data.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from config.settings import settings
from backend.models.models import Region, HotspotResult, utc_now
from backend.services.storage_service import get_historical_observations
from backend.services.region_service import get_region_by_identifier
from backend.utils.logger import logger


def calculate_hotspot_level_and_color(score: float) -> Tuple[str, str, bool]:
    """
    Classifies a composite hotspot score (0.0 to 1.0) into explainable categories.
    """
    if score >= 0.80:
        return "SEVERE HOTSPOT", "#dc2626", True
    elif score >= settings.HOTSPOT_SCORE_THRESHOLD:
        return "HOTSPOT", "#ea580c", True
    elif score >= 0.40:
        return "ELEVATED", "#d97706", False
    else:
        return "NORMAL", "#10b981", False


def evaluate_region_hotspot(
    region: Region,
    latest_obs: Dict[str, Any],
    recent_obs: List[Dict[str, Any]],
    multi_region_aqi_mean: float,
    multi_region_aqi_std: float
) -> Dict[str, Any]:
    """
    Evaluates an individual region across the 4 explainable hotspot scoring pillars:
    1. Current AQI severity
    2. Relative deviation against monitored regional average
    3. Deviation against the region's own recent baseline
    4. Persistence of elevated readings over the historical window
    """
    current_aqi = float(latest_obs.get("aqi", 0.0) or 0.0)
    current_pm25 = latest_obs.get("pm25")
    current_pm10 = latest_obs.get("pm10")

    obs_count = len(recent_obs)
    reasons: List[str] = []

    # 1. AQI Severity Component (Normalized to 300 scale)
    # 0 = clean, 100 = 0.33, 200 = 0.67, 300+ = 1.0
    s_aqi = min(1.0, max(0.0, current_aqi / 300.0))

    # 2. Regional Relative Deviation Component
    # Compares current region to the average across all monitored cities
    if multi_region_aqi_std > 0:
        rel_diff = current_aqi - multi_region_aqi_mean
        s_rel = min(1.0, max(0.0, (rel_diff / (2.0 * max(multi_region_aqi_std, 15.0))) + 0.5))
    else:
        s_rel = 0.5

    if current_aqi > multi_region_aqi_mean + 10.0:
        reasons.append(
            f"Current AQI ({round(current_aqi)}) is {round(current_aqi - multi_region_aqi_mean)} points above the monitored regional average ({round(multi_region_aqi_mean)})."
        )
    elif current_aqi < multi_region_aqi_mean - 10.0:
        reasons.append(
            f"Current AQI ({round(current_aqi)}) is {round(multi_region_aqi_mean - current_aqi)} points below the monitored regional average ({round(multi_region_aqi_mean)})."
        )
    else:
        reasons.append(f"Current AQI ({round(current_aqi)}) is aligned with regional average ({round(multi_region_aqi_mean)}).")

    # 3. Historical Baseline Deviation Component
    # Compares to the region's own historical average over the analysis window
    if obs_count > 0:
        valid_hist_aqi = [float(o["aqi"]) for o in recent_obs if o.get("aqi") is not None]
        local_mean = float(np.mean(valid_hist_aqi)) if valid_hist_aqi else current_aqi
    else:
        local_mean = current_aqi

    denom_local = max(local_mean, 25.0)
    s_hist = min(1.0, max(0.0, (current_aqi / denom_local) - 0.5))

    if current_aqi > local_mean + 15.0:
        reasons.append(
            f"Elevated above local {settings.HOTSPOT_HISTORY_HOURS}h baseline mean of {round(local_mean, 1)} (+{round(current_aqi - local_mean, 1)} deviation)."
        )
    elif current_aqi < local_mean - 15.0:
        reasons.append(
            f"Favorable atmospheric clearance: {round(local_mean - current_aqi, 1)} points below local {settings.HOTSPOT_HISTORY_HOURS}h baseline mean."
        )

    # 4. Persistence Component
    # Fraction of observations over the window where AQI was elevated (>= 100)
    if obs_count > 0:
        elevated_obs = sum(1 for o in recent_obs if o.get("aqi") is not None and float(o["aqi"]) >= 100.0)
        s_pers = elevated_obs / float(obs_count)
        pct_pers = round(s_pers * 100.0)
        if pct_pers >= 50:
            reasons.append(
                f"High persistence: {pct_pers}% of observations in the past {settings.HOTSPOT_HISTORY_HOURS}h exceeded the unhealthy threshold."
            )
    else:
        s_pers = 0.0

    # Pollutant driver context
    if current_pm25 is not None and current_pm25 > 60.0:
        reasons.append(f"Fine particulate matter PM2.5 ({current_pm25} µg/m³) is a primary atmospheric driver.")

    # Composite Hotspot Score:
    # 35% Current AQI Severity + 25% Relative Regional + 20% Historical Baseline + 20% Persistence
    composite_score = round(0.35 * s_aqi + 0.25 * s_rel + 0.20 * s_hist + 0.20 * s_pers, 2)
    level, color, is_hotspot = calculate_hotspot_level_and_color(composite_score)

    explanation = " | ".join(reasons) if reasons else "Air quality is within normal parameters."

    return {
        "region_id": region.id,
        "region": region.name,
        "latitude": region.latitude,
        "longitude": region.longitude,
        "current_aqi": round(current_aqi, 1),
        "pm25": current_pm25,
        "pm10": current_pm10,
        "hotspot_score": composite_score,
        "level": level,
        "level_color": color,
        "is_hotspot": is_hotspot,
        "components": {
            "aqi_severity": round(s_aqi, 2),
            "relative_deviation": round(s_rel, 2),
            "historical_deviation": round(s_hist, 2),
            "persistence": round(s_pers, 2)
        },
        "reasons": reasons,
        "explanation": explanation,
        "observations_used": obs_count
    }


def assess_hotspots(
    db: Session,
    hours: Optional[int] = None,
    persist: bool = True
) -> Dict[str, Any]:
    """
    Performs dynamic multi-region hotspot detection across all monitored cities.
    Calculates regional cross-sectional statistics, scores each region,
    ranks by severity, and returns map-ready coordinates.
    """
    logger.info("Hotspot analysis started: Evaluating monitored regions...")
    hours_window = hours or settings.HOTSPOT_HISTORY_HOURS
    regions = db.query(Region).filter(Region.is_active == True).all()

    if not regions:
        return {
            "success": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "range": f"{hours_window}h",
            "total_regions_analyzed": 0,
            "hotspots_count": 0,
            "highest_hotspot_region": None,
            "hotspots": []
        }

    # Step 1: Collect recent and latest telemetry for all regions
    region_data = []
    latest_aqis = []

    for r in regions:
        # Retrieve bounded historical observations for this region
        obs = get_historical_observations(db, region_id=r.id, hours=hours_window, limit=200)
        if obs:
            latest = obs[-1]
            aq_val = latest.get("aqi")
            if aq_val is not None:
                latest_aqis.append(float(aq_val))
        else:
            latest = {}

        region_data.append({
            "region": r,
            "latest": latest,
            "recent": obs
        })

    # Step 2: Calculate cross-sectional multi-region baseline statistics
    if latest_aqis:
        multi_mean = float(np.mean(latest_aqis))
        multi_std = float(np.std(latest_aqis))
    else:
        multi_mean = 75.0
        multi_std = 20.0

    # Step 3: Evaluate each region
    scored_regions = []
    for item in region_data:
        res = evaluate_region_hotspot(
            region=item["region"],
            latest_obs=item["latest"],
            recent_obs=item["recent"],
            multi_region_aqi_mean=multi_mean,
            multi_region_aqi_std=multi_std
        )
        scored_regions.append(res)

    # Step 4: Rank dynamically by hotspot score descending
    scored_regions.sort(key=lambda x: (x["hotspot_score"], x["current_aqi"]), reverse=True)

    # Assign ranks
    for idx, item in enumerate(scored_regions, start=1):
        item["rank"] = idx

    hotspots_count = sum(1 for x in scored_regions if x["is_hotspot"])
    highest_region = scored_regions[0]["region"] if scored_regions else None

    # Step 5: Optional persistence of hotspot results
    if persist and scored_regions:
        try:
            for item in scored_regions:
                hr = HotspotResult(
                    region_id=item["region_id"],
                    timestamp=utc_now(),
                    hotspot_score=item["hotspot_score"],
                    level=item["level"],
                    aqi=item["current_aqi"],
                    method_version="v1.0"
                )
                db.add(hr)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Non-blocking error persisting hotspot results: {e}")

    logger.info(
        f"Hotspot analysis completed: {len(scored_regions)} regions analyzed, "
        f"{hotspots_count} active hotspots flagged. Top region: {highest_region}"
    )

    return {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range": f"{hours_window}h",
        "total_regions_analyzed": len(scored_regions),
        "hotspots_count": hotspots_count,
        "highest_hotspot_region": highest_region,
        "hotspots": scored_regions
    }


def get_regional_hotspot_detail(
    db: Session,
    region_identifier: Any,
    hours: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Retrieves hotspot assessment details for a specific region."""
    reg = get_region_by_identifier(db, region_identifier)
    if not reg:
        return None

    full_assessment = assess_hotspots(db, hours=hours, persist=False)
    for h in full_assessment.get("hotspots", []):
        if h["region_id"] == reg.id:
            return h
    return None
