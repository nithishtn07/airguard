"""
AirGuard AI - Data Collector Interface
--------------------------------------
This module serves as the architectural contract for Phase 2:
- Real-time Air Quality Data Collection (e.g. OpenAQ, CPCB, or external APIs)
- Real-time Weather Data Collection (e.g. OpenWeatherMap, Meteo APIs)

NOTE: Implementation scheduled for Phase 2. No live or fake data in Phase 1.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseDataCollector(ABC):
    """Abstract Base Class for environmental data collectors."""

    @abstractmethod
    def fetch_air_quality(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch live air quality telemetry for the given coordinates."""
        pass

    @abstractmethod
    def fetch_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch live meteorological conditions for the given coordinates."""
        pass


class OpenMeteoDataCollector(BaseDataCollector):
    """
    Concrete implementation of BaseDataCollector leveraging Open-Meteo APIs.
    """
    def fetch_air_quality(self, latitude: float, longitude: float) -> Dict[str, Any]:
        from backend.models.models import Region
        temp_region = Region(id=0, name="Coordinate Query", latitude=latitude, longitude=longitude)
        from backend.services.air_quality_service import fetch_live_air_quality
        return fetch_live_air_quality(temp_region).model_dump()

    def fetch_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        from backend.models.models import Region
        temp_region = Region(id=0, name="Coordinate Query", latitude=latitude, longitude=longitude)
        from backend.services.weather_service import fetch_live_weather
        return fetch_live_weather(temp_region).model_dump()


# Singleton collector instance
collector = OpenMeteoDataCollector()

