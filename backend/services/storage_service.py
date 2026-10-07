from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, asc

from backend.models.models import Region, AirQualityObservation, WeatherObservation, utc_now
from backend.models.schemas import AirQualityData, WeatherData
from backend.utils.logger import logger


def _parse_iso_timestamp(ts_str: str) -> datetime:
    """Parses an ISO 8601 string into a timezone-aware datetime in UTC."""
    if isinstance(ts_str, datetime):
        dt = ts_str
    else:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def save_air_quality_observation(
    db: Session,
    region_id: int,
    aq_data: AirQualityData
) -> Tuple[AirQualityObservation, bool]:
    """
    Stores an air quality observation with strict duplicate prevention.
    Returns (record, is_new).
    """
    obs_time = _parse_iso_timestamp(aq_data.timestamp)

    # 1. Duplicate check (region_id + observation timestamp + source)
    existing = (
        db.query(AirQualityObservation)
        .filter(
            AirQualityObservation.region_id == region_id,
            AirQualityObservation.timestamp == obs_time,
            AirQualityObservation.source == aq_data.source
        )
        .first()
    )
    if existing:
        logger.debug(f"Duplicate air quality observation skipped for region {region_id} at {obs_time}")
        return existing, False

    # 2. Persist new record
    obs = AirQualityObservation(
        region_id=region_id,
        timestamp=obs_time,
        created_at=utc_now(),
        aqi=aq_data.aqi,
        pm2_5=aq_data.pm25,
        pm10=aq_data.pm10,
        co=aq_data.co,
        no2=aq_data.no2,
        so2=aq_data.so2,
        o3=aq_data.o3,
        source=aq_data.source
    )
    try:
        db.add(obs)
        db.commit()
        db.refresh(obs)
        logger.info(f"Stored air quality observation: region {region_id}, timestamp {obs_time}, AQI={obs.aqi}")
        return obs, True
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(AirQualityObservation)
            .filter(
                AirQualityObservation.region_id == region_id,
                AirQualityObservation.timestamp == obs_time,
                AirQualityObservation.source == aq_data.source
            )
            .first()
        )
        return existing, False


def save_weather_observation(
    db: Session,
    region_id: int,
    weather_data: WeatherData
) -> Tuple[WeatherObservation, bool]:
    """
    Stores a weather observation with strict duplicate prevention.
    Returns (record, is_new).
    """
    obs_time = _parse_iso_timestamp(weather_data.timestamp)

    # 1. Duplicate check
    existing = (
        db.query(WeatherObservation)
        .filter(
            WeatherObservation.region_id == region_id,
            WeatherObservation.timestamp == obs_time,
            WeatherObservation.source == weather_data.source
        )
        .first()
    )
    if existing:
        logger.debug(f"Duplicate weather observation skipped for region {region_id} at {obs_time}")
        return existing, False

    # 2. Persist new record
    obs = WeatherObservation(
        region_id=region_id,
        timestamp=obs_time,
        created_at=utc_now(),
        temperature=weather_data.temperature,
        humidity=weather_data.humidity,
        wind_speed=weather_data.wind_speed,
        wind_direction=weather_data.wind_direction,
        pressure=weather_data.pressure,
        rainfall=weather_data.rainfall,
        source=weather_data.source
    )
    try:
        db.add(obs)
        db.commit()
        db.refresh(obs)
        logger.info(f"Stored weather observation: region {region_id}, timestamp {obs_time}, Temp={obs.temperature}")
        return obs, True
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(WeatherObservation)
            .filter(
                WeatherObservation.region_id == region_id,
                WeatherObservation.timestamp == obs_time,
                WeatherObservation.source == weather_data.source
            )
            .first()
        )
        return existing, False


def save_environmental_snapshot(
    db: Session,
    region_id: int,
    aq_data: AirQualityData,
    weather_data: WeatherData
) -> Dict[str, Any]:
    """
    Persists both air quality and weather telemetry for a region in one transactional call.
    """
    aq_record, aq_is_new = save_air_quality_observation(db, region_id, aq_data)
    weather_record, weather_is_new = save_weather_observation(db, region_id, weather_data)

    return {
        "region_id": region_id,
        "aq_record_id": aq_record.id if aq_record else None,
        "aq_is_new": aq_is_new,
        "weather_record_id": weather_record.id if weather_record else None,
        "weather_is_new": weather_is_new
    }


def get_historical_observations(
    db: Session,
    region_id: int,
    hours: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Retrieves chronological environmental observations for a region.
    Applies time filtering and aligns air quality and weather records.
    """
    aq_query = db.query(AirQualityObservation).filter(AirQualityObservation.region_id == region_id)
    weather_query = db.query(WeatherObservation).filter(WeatherObservation.region_id == region_id)

    if hours is not None and hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        aq_query = aq_query.filter(AirQualityObservation.timestamp >= cutoff)
        weather_query = weather_query.filter(WeatherObservation.timestamp >= cutoff)
    else:
        if start:
            aq_query = aq_query.filter(AirQualityObservation.timestamp >= start)
            weather_query = weather_query.filter(WeatherObservation.timestamp >= start)
        if end:
            aq_query = aq_query.filter(AirQualityObservation.timestamp <= end)
            weather_query = weather_query.filter(WeatherObservation.timestamp <= end)

    aq_records = aq_query.order_by(asc(AirQualityObservation.timestamp)).limit(limit).all()
    weather_records = weather_query.order_by(asc(WeatherObservation.timestamp)).limit(limit).all()

    # Index weather records by timestamp (or nearest match)
    weather_map: Dict[str, WeatherObservation] = {
        w.timestamp.isoformat(): w for w in weather_records
    }

    results: List[Dict[str, Any]] = []

    # Map aligned observations
    for aq in aq_records:
        ts_iso = aq.timestamp.isoformat()
        w = weather_map.get(ts_iso)

        # Fallback to nearest weather record if exact second doesn't match
        if not w and weather_records:
            # find closest within 3600 seconds
            closest = min(weather_records, key=lambda x: abs((x.timestamp - aq.timestamp).total_seconds()))
            if abs((closest.timestamp - aq.timestamp).total_seconds()) <= 3600:
                w = closest

        item = {
            "timestamp": ts_iso,
            "created_at": aq.created_at.isoformat() if aq.created_at else None,
            "aqi": aq.aqi,
            "pm25": aq.pm2_5,
            "pm10": aq.pm10,
            "co": aq.co,
            "no2": aq.no2,
            "so2": aq.so2,
            "o3": aq.o3,
            "temperature": w.temperature if w else None,
            "humidity": w.humidity if w else None,
            "wind_speed": w.wind_speed if w else None,
            "wind_direction": w.wind_direction if w else None,
            "pressure": w.pressure if w else None,
            "rainfall": w.rainfall if w else None,
            "aq_source": aq.source,
            "weather_source": w.source if w else None
        }
        results.append(item)

    return results


def get_database_stats(db: Session) -> Dict[str, Any]:
    """
    Returns actual counts and timestamp spans of real observations in the database.
    """
    regions = db.query(Region).all()
    total_aq = db.query(AirQualityObservation).count()
    total_weather = db.query(WeatherObservation).count()

    earliest_aq = db.query(AirQualityObservation.timestamp).order_by(asc(AirQualityObservation.timestamp)).first()
    latest_aq = db.query(AirQualityObservation.timestamp).order_by(desc(AirQualityObservation.timestamp)).first()

    region_stats = []
    for r in regions:
        aq_count = db.query(AirQualityObservation).filter(AirQualityObservation.region_id == r.id).count()
        w_count = db.query(WeatherObservation).filter(WeatherObservation.region_id == r.id).count()
        region_stats.append({
            "region_id": r.id,
            "name": r.name,
            "aq_observations": aq_count,
            "weather_observations": w_count
        })

    return {
        "total_air_quality_records": total_aq,
        "total_weather_records": total_weather,
        "earliest_timestamp": earliest_aq[0].isoformat() if earliest_aq else None,
        "latest_timestamp": latest_aq[0].isoformat() if latest_aq else None,
        "regions": region_stats
    }
