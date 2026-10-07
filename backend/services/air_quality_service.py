import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from config.settings import settings
from backend.models.schemas import AirQualityData
from backend.models.models import Region
from backend.utils.logger import logger
from backend.utils.cache import cache


def _sanitize_metric(val: Any, min_val: float = 0.0, max_val: Optional[float] = None) -> Optional[float]:
    """
    Validates and sanitizes a numerical measurement.
    Returns float or None if missing, invalid, or out of physical bounds.
    """
    if val is None:
        return None
    try:
        f = float(val)
        if f < min_val:
            return None
        if max_val is not None and f > max_val:
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def fetch_live_air_quality(
    region: Region,
    force_refresh: bool = False
) -> AirQualityData:
    """
    Fetches, validates, and normalizes live atmospheric air quality telemetry.
    Uses Open-Meteo Air Quality API (Copernicus CAMS & WMO).
    """
    cache_key = f"air_quality_{region.id}"
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Serving cached air quality for {region.name}")
            return cached

    url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={region.latitude}&longitude={region.longitude}&"
        f"current=us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
    )

    headers = {
        "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise RuntimeError(f"Air quality upstream returned status {response.status}")
            raw_bytes = response.read()
            payload = json.loads(raw_bytes.decode("utf-8"))
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            logger.error(f"Air quality external API timed out for {region.name}: {e}")
            raise TimeoutError("Air-quality service timed out.")
        logger.error(f"Air quality network failure for {region.name}: {e}")
        raise RuntimeError("Live air-quality data currently unavailable.")
    except TimeoutError as te:
        logger.error(f"Air quality external API timed out for {region.name}: {te}")
        raise TimeoutError("Air-quality service timed out.")
    except Exception as e:
        logger.error(f"Error fetching air quality for {region.name}: {e}")
        raise RuntimeError("Live air-quality data currently unavailable.")

    current = payload.get("current", {})
    if not current:
        logger.warning(f"No 'current' block in air quality response for {region.name}")
        raise ValueError("Malformed atmospheric data payload received from provider.")

    # Normalize observation timestamp to ISO 8601 UTC
    raw_time = current.get("time")
    obs_time_iso = datetime.now(timezone.utc).isoformat()
    if raw_time:
        try:
            # Open-Meteo time is typically 'YYYY-MM-DDTHH:MM' in UTC
            dt = datetime.fromisoformat(raw_time)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            obs_time_iso = dt.isoformat()
        except Exception:
            pass

    # Validate and normalize atmospheric pollutants
    aqi_val = _sanitize_metric(current.get("us_aqi"), min_val=0, max_val=1000)
    pm25_val = _sanitize_metric(current.get("pm2_5"), min_val=0, max_val=2000)
    pm10_val = _sanitize_metric(current.get("pm10"), min_val=0, max_val=3000)
    co_val = _sanitize_metric(current.get("carbon_monoxide"), min_val=0, max_val=50000)
    no2_val = _sanitize_metric(current.get("nitrogen_dioxide"), min_val=0, max_val=2000)
    so2_val = _sanitize_metric(current.get("sulphur_dioxide"), min_val=0, max_val=2000)
    o3_val = _sanitize_metric(current.get("ozone"), min_val=0, max_val=2000)

    source_label = "Open-Meteo Air Quality (Copernicus CAMS)"

    data = AirQualityData(
        region=region.name,
        region_id=region.id,
        timestamp=obs_time_iso,
        aqi=aqi_val,
        pm25=pm25_val,
        pm10=pm10_val,
        co=co_val,
        no2=no2_val,
        so2=so2_val,
        o3=o3_val,
        source=source_label
    )

    # Save to short-lived cache
    cache.set(cache_key, data)
    return data
