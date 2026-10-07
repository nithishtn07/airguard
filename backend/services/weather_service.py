import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Any

from config.settings import settings
from backend.models.schemas import WeatherData
from backend.models.models import Region
from backend.utils.logger import logger
from backend.utils.cache import cache


def _sanitize_metric(val: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Optional[float]:
    """
    Validates and sanitizes a weather measurement.
    Returns float or None if missing or out of valid physical bounds.
    """
    if val is None:
        return None
    try:
        f = float(val)
        if min_val is not None and f < min_val:
            return None
        if max_val is not None and f > max_val:
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def fetch_live_weather(
    region: Region,
    force_refresh: bool = False
) -> WeatherData:
    """
    Fetches, validates, and normalizes live meteorological conditions.
    Uses Open-Meteo Weather Model (WMO standards).
    """
    cache_key = f"weather_{region.id}"
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Serving cached weather for {region.name}")
            return cached

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={region.latitude}&longitude={region.longitude}&"
        f"current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation"
    )

    headers = {
        "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise RuntimeError(f"Weather upstream returned status {response.status}")
            raw_bytes = response.read()
            payload = json.loads(raw_bytes.decode("utf-8"))
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            logger.error(f"Weather external API timed out for {region.name}: {e}")
            raise TimeoutError("Weather service timed out.")
        logger.error(f"Weather network failure for {region.name}: {e}")
        raise RuntimeError("Live weather data currently unavailable.")
    except TimeoutError as te:
        logger.error(f"Weather external API timed out for {region.name}: {te}")
        raise TimeoutError("Weather service timed out.")
    except Exception as e:
        logger.error(f"Error fetching weather for {region.name}: {e}")
        raise RuntimeError("Live weather data currently unavailable.")

    current = payload.get("current", {})
    if not current:
        logger.warning(f"No 'current' block in weather response for {region.name}")
        raise ValueError("Malformed meteorological data payload received from provider.")

    # Normalize observation timestamp to ISO 8601 UTC
    raw_time = current.get("time")
    obs_time_iso = datetime.now(timezone.utc).isoformat()
    if raw_time:
        try:
            dt = datetime.fromisoformat(raw_time)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            obs_time_iso = dt.isoformat()
        except Exception:
            pass

    # Validate and normalize meteorological variables
    temp_val = _sanitize_metric(current.get("temperature_2m"), min_val=-90, max_val=65)
    humidity_val = _sanitize_metric(current.get("relative_humidity_2m"), min_val=0, max_val=100)
    wind_speed_val = _sanitize_metric(current.get("wind_speed_10m"), min_val=0, max_val=400)
    wind_direction_val = _sanitize_metric(current.get("wind_direction_10m"), min_val=0, max_val=360)
    pressure_val = _sanitize_metric(current.get("surface_pressure"), min_val=500, max_val=1200)
    rainfall_val = _sanitize_metric(current.get("precipitation"), min_val=0, max_val=1000)

    source_label = "Open-Meteo Weather Model (WMO)"

    data = WeatherData(
        region=region.name,
        region_id=region.id,
        timestamp=obs_time_iso,
        temperature=temp_val,
        humidity=humidity_val,
        wind_speed=wind_speed_val,
        wind_direction=wind_direction_val,
        pressure=pressure_val,
        rainfall=rainfall_val,
        source=source_label
    )

    # Save to short-lived cache
    cache.set(cache_key, data)
    return data
