import json
import math
import urllib.parse
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from config.settings import settings
from backend.services.region_service import DEFAULT_REGIONS
from backend.utils.logger import logger
from backend.utils.cache import cache


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_matching_default_region(latitude: float, longitude: float, max_km: float = 25.0) -> Optional[Dict[str, Any]]:
    """
    Checks if given coordinates are within max_km of any pre-configured default region.
    Returns matched region dict with 1-based region ID, or None.
    """
    for idx, reg in enumerate(DEFAULT_REGIONS, start=1):
        dist = _distance_km(latitude, longitude, reg["latitude"], reg["longitude"])
        if dist <= max_km:
            return {
                "id": idx,
                "name": reg["name"],
                "state": reg["state"],
                "country": reg["country"],
                "distance_km": round(dist, 2)
            }
    return None


def search_locations(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches for locations matching a text query using open geocoding.
    Prioritizes pre-configured regions when relevant, followed by geocoding API.
    """
    clean_query = (query or "").strip()
    if not clean_query or len(clean_query) < 2:
        return []

    cache_key = f"geocode_search_{clean_query.lower()}_{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    results: List[Dict[str, Any]] = []

    # 1. Check local pre-configured regions for immediate exact or partial match
    q_lower = clean_query.lower()
    for idx, reg in enumerate(DEFAULT_REGIONS, start=1):
        if q_lower in reg["name"].lower() or q_lower in reg["state"].lower():
            results.append({
                "name": reg["name"],
                "display_name": f"{reg['name']}, {reg['state']}, {reg['country']}",
                "latitude": reg["latitude"],
                "longitude": reg["longitude"],
                "state": reg["state"],
                "country": reg["country"],
                "matched_region_id": idx,
                "is_default_monitored": True
            })

    # 2. Query Open-Meteo Geocoding API (free, reliable, global coverage, no API key required)
    encoded = urllib.parse.quote(clean_query)
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count={limit}&language=en&format=json"
    headers = {"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION} (environmental-geocoding)"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                api_items = payload.get("results", [])
                for item in api_items:
                    lat = float(item["latitude"])
                    lon = float(item["longitude"])
                    name = item.get("name", clean_query)
                    state = item.get("admin1") or item.get("admin2") or ""
                    country = item.get("country", "")

                    parts = [name]
                    if state:
                        parts.append(state)
                    if country:
                        parts.append(country)
                    display_name = ", ".join(parts)

                    # Check proximity to known default regions
                    matched = find_matching_default_region(lat, lon)
                    matched_id = matched["id"] if matched else None

                    # Avoid exact coordinate duplicates with local matches
                    if not any(abs(r["latitude"] - lat) < 0.001 and abs(r["longitude"] - lon) < 0.001 for r in results):
                        results.append({
                            "name": name,
                            "display_name": display_name,
                            "latitude": round(lat, 4),
                            "longitude": round(lon, 4),
                            "state": state,
                            "country": country,
                            "matched_region_id": matched_id,
                            "is_default_monitored": matched_id is not None
                        })
    except Exception as e:
        logger.warning(f"Geocoding external search error for '{clean_query}': {e}")

    # Fallback to Nominatim if zero results found
    if not results:
        nom_url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit={limit}"
        try:
            req = urllib.request.Request(nom_url, headers=headers)
            with urllib.request.urlopen(req, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    nom_items = json.loads(resp.read().decode("utf-8"))
                    for n in nom_items:
                        lat = float(n["lat"])
                        lon = float(n["lon"])
                        matched = find_matching_default_region(lat, lon)
                        results.append({
                            "name": n.get("name") or n.get("display_name", "").split(",")[0],
                            "display_name": n.get("display_name", clean_query),
                            "latitude": round(lat, 4),
                            "longitude": round(lon, 4),
                            "state": "",
                            "country": "",
                            "matched_region_id": matched["id"] if matched else None,
                            "is_default_monitored": matched is not None
                        })
        except Exception as ex:
            logger.debug(f"Nominatim fallback notice: {ex}")

    trimmed = results[:limit]
    cache.set(cache_key, trimmed, ttl=3600)
    return trimmed


def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Performs reverse geocoding for coordinates to determine place name, state, and country.
    Validates geographical limits and links to monitored regions where nearby.
    """
    # 1. Coordinate validation
    if latitude < -90.0 or latitude > 90.0 or longitude < -180.0 or longitude > 180.0:
        raise ValueError(f"Invalid geographical coordinates: lat={latitude}, lon={longitude}")

    lat_r = round(latitude, 4)
    lon_r = round(longitude, 4)
    cache_key = f"reverse_geo_{lat_r}_{lon_r}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 2. Check proximity to local pre-configured regions
    matched = find_matching_default_region(lat_r, lon_r, max_km=15.0)

    # 3. Query Nominatim reverse geocoder
    headers = {"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION} (environmental-model)"}
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat_r}&lon={lon_r}&format=json"

    result = {
        "name": f"Location ({lat_r}, {lon_r})",
        "display_name": f"{lat_r}° N, {lon_r}° E",
        "latitude": lat_r,
        "longitude": lon_r,
        "city": None,
        "state": None,
        "country": "India" if (8.0 <= lat_r <= 37.0 and 68.0 <= lon_r <= 97.5) else "Unknown",
        "matched_region_id": matched["id"] if matched else None,
        "is_default_monitored": matched is not None
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                addr = data.get("address", {})
                city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb") or addr.get("county")
                state = addr.get("state")
                country = addr.get("country", result["country"])
                disp = data.get("display_name")

                if city:
                    result["name"] = city
                elif matched:
                    result["name"] = matched["name"]

                result["city"] = city
                result["state"] = state or (matched["state"] if matched else None)
                result["country"] = country
                result["display_name"] = disp or f"{result['name']}, {result['state']}, {result['country']}"
    except Exception as e:
        logger.warning(f"Reverse geocode network fallback for ({lat_r}, {lon_r}): {e}")
        if matched:
            result["name"] = matched["name"]
            result["state"] = matched["state"]
            result["display_name"] = f"{matched['name']}, {matched['state']}, India"

    cache.set(cache_key, result, ttl=86400)
    return result


class GeocodingService:
    """Service wrapper for geocoding functions."""

    def search_locations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return search_locations(query, limit)

    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        return reverse_geocode(lat, lon)


geocoding_service = GeocodingService()
