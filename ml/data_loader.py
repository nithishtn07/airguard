"""
AirGuard AI - ML Data Loader Module (Phase 4)
---------------------------------------------
Loads and validates real historical observations from the SQLite database.
Includes real-data synchronization from Copernicus CAMS & Open-Meteo to populate
genuine atmospheric records without fabricating synthetic data.
"""
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from config.settings import settings
from database.session import SessionLocal
from backend.models.models import Region, AirQualityObservation, WeatherObservation
from backend.models.schemas import AirQualityData, WeatherData
from backend.services.storage_service import (
    get_historical_observations,
    save_air_quality_observation,
    save_weather_observation
)
from backend.utils.logger import logger


def load_historical_data(
    region_id: Optional[int] = None,
    db: Optional[Session] = None,
    limit: int = 10000
) -> pd.DataFrame:
    """
    Extracts raw historical records from database for a specific region or all regions.
    Guarantees strict chronological sorting.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        if region_id is not None:
            raw = get_historical_observations(db, region_id=region_id, limit=limit)
            df = pd.DataFrame(raw)
            if not df.empty:
                df["region_id"] = region_id
        else:
            # Load observations across all active regions
            regions = db.query(Region).filter(Region.is_active == True).all()
            all_records = []
            for r in regions:
                r_obs = get_historical_observations(db, region_id=r.id, limit=limit)
                for item in r_obs:
                    item["region_id"] = r.id
                    item["region_name"] = r.name
                all_records.extend(r_obs)
            df = pd.DataFrame(all_records)

        if df.empty:
            return pd.DataFrame()

        # Enforce chronological ordering by observation timestamp
        df["dt"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
        df = df.sort_values("dt", ascending=True).reset_index(drop=True)
        df = df.drop(columns=["dt"])
        return df
    finally:
        if should_close:
            db.close()


def check_data_sufficiency(df: pd.DataFrame, min_rows: Optional[int] = None) -> Dict[str, Any]:
    """
    Audits the real dataset before model training.
    Validates minimum sample size, non-null target observations, and time range.
    """
    threshold = min_rows if min_rows is not None else settings.MIN_TRAINING_ROWS
    total_records = len(df) if df is not None else 0

    if total_records == 0:
        return {
            "is_sufficient": False,
            "total_records": 0,
            "valid_aqi_records": 0,
            "min_required": threshold,
            "time_range": {"start": None, "end": None},
            "message": f"Insufficient historical data: 0 records found. Minimum required is {threshold}."
        }

    valid_aqi = int(df["aqi"].dropna().count()) if "aqi" in df.columns else 0
    t_start = str(df["timestamp"].min()) if "timestamp" in df.columns else None
    t_end = str(df["timestamp"].max()) if "timestamp" in df.columns else None

    is_sufficient = valid_aqi >= threshold
    msg = (
        f"Dataset sufficient for training ({valid_aqi} valid AQI observations >= {threshold} threshold)."
        if is_sufficient
        else f"Insufficient historical data for training: {valid_aqi} observations found, minimum required is {threshold}."
    )

    return {
        "is_sufficient": is_sufficient,
        "total_records": total_records,
        "valid_aqi_records": valid_aqi,
        "min_required": threshold,
        "time_range": {"start": t_start, "end": t_end},
        "message": msg
    }


def sync_real_historical_telemetry(db: Session, region: Region, past_days: int = 7) -> int:
    """
    Ingests genuine historical observations from Open-Meteo & Copernicus CAMS
    into the database with idempotent duplicate prevention.
    Strictly real atmospheric telemetry — NO synthetic values.
    """
    logger.info(f"Syncing {past_days} days of real telemetry for {region.name}...")
    inserted_count = 0

    # 1. Fetch real hourly atmospheric pollution from Copernicus CAMS via Open-Meteo
    aq_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={region.latitude}&longitude={region.longitude}&"
        f"past_days={past_days}&"
        f"hourly=us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
    )

    # 2. Fetch real hourly meteorological conditions from Open-Meteo
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={region.latitude}&longitude={region.longitude}&"
        f"past_days={past_days}&"
        f"hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation"
    )

    headers = {"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"}

    try:
        req_aq = urllib.request.Request(aq_url, headers=headers)
        with urllib.request.urlopen(req_aq, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS * 2) as resp:
            aq_payload = json.loads(resp.read().decode("utf-8"))

        req_w = urllib.request.Request(weather_url, headers=headers)
        with urllib.request.urlopen(req_w, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS * 2) as resp:
            w_payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to fetch real telemetry for {region.name}: {e}")
        return 0

    aq_hourly = aq_payload.get("hourly", {})
    w_hourly = w_payload.get("hourly", {})

    aq_times = aq_hourly.get("time", [])
    w_times = w_hourly.get("time", [])

    # Map weather values by timestamp string for alignment
    w_map = {}
    for i, t in enumerate(w_times):
        w_map[t] = {
            "temperature": w_hourly.get("temperature_2m", [None])[i],
            "humidity": w_hourly.get("relative_humidity_2m", [None])[i],
            "wind_speed": w_hourly.get("wind_speed_10m", [None])[i],
            "wind_direction": w_hourly.get("wind_direction_10m", [None])[i],
            "pressure": w_hourly.get("surface_pressure", [None])[i],
            "rainfall": w_hourly.get("precipitation", [None])[i],
        }

    # Store real observations
    for i, t_str in enumerate(aq_times):
        # Format to UTC ISO timestamp
        try:
            dt = datetime.fromisoformat(t_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            iso_ts = dt.isoformat()
        except Exception:
            iso_ts = t_str + "+00:00"

        aqi_val = aq_hourly.get("us_aqi", [None])[i]
        pm25_val = aq_hourly.get("pm2_5", [None])[i]
        pm10_val = aq_hourly.get("pm10", [None])[i]
        co_val = aq_hourly.get("carbon_monoxide", [None])[i]
        no2_val = aq_hourly.get("nitrogen_dioxide", [None])[i]
        so2_val = aq_hourly.get("sulphur_dioxide", [None])[i]
        o3_val = aq_hourly.get("ozone", [None])[i]

        aq_obj = AirQualityData(
            region=region.name,
            region_id=region.id,
            timestamp=iso_ts,
            aqi=float(aqi_val) if aqi_val is not None else None,
            pm25=float(pm25_val) if pm25_val is not None else None,
            pm10=float(pm10_val) if pm10_val is not None else None,
            co=float(co_val) if co_val is not None else None,
            no2=float(no2_val) if no2_val is not None else None,
            so2=float(so2_val) if so2_val is not None else None,
            o3=float(o3_val) if o3_val is not None else None,
            source="Copernicus-CAMS-OpenMeteo-Archive"
        )
        _, is_new_aq = save_air_quality_observation(db, region.id, aq_obj)

        w_vals = w_map.get(t_str, {})
        w_obj = WeatherData(
            region=region.name,
            region_id=region.id,
            timestamp=iso_ts,
            temperature=float(w_vals["temperature"]) if w_vals.get("temperature") is not None else None,
            humidity=float(w_vals["humidity"]) if w_vals.get("humidity") is not None else None,
            wind_speed=float(w_vals["wind_speed"]) if w_vals.get("wind_speed") is not None else None,
            wind_direction=float(w_vals["wind_direction"]) if w_vals.get("wind_direction") is not None else None,
            pressure=float(w_vals["pressure"]) if w_vals.get("pressure") is not None else None,
            rainfall=float(w_vals["rainfall"]) if w_vals.get("rainfall") is not None else None,
            source="OpenMeteo-Weather-Archive"
        )
        _, is_new_w = save_weather_observation(db, region.id, w_obj)

        if is_new_aq or is_new_w:
            inserted_count += 1

    logger.info(f"Sync complete for {region.name}: {inserted_count} new observations stored.")
    return inserted_count


def sync_all_regions(db: Session, past_days: int = 7) -> Dict[str, int]:
    """Syncs real historical observations for all active regions."""
    regions = db.query(Region).filter(Region.is_active == True).all()
    results = {}
    for r in regions:
        cnt = sync_real_historical_telemetry(db, r, past_days=past_days)
        results[r.name] = cnt
    return results
