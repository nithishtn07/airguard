from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class Region(Base):
    """
    Region entity representing geographical locations monitored by AirGuard AI.
    """
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    air_quality_records = relationship("AirQualityObservation", back_populates="region", cascade="all, delete-orphan")
    weather_records = relationship("WeatherObservation", back_populates="region", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="region", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="region", cascade="all, delete-orphan")
    hotspot_results = relationship("HotspotResult", back_populates="region", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="region", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "state": self.state,
            "country": self.country,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# =====================================================================
# HISTORICAL ENVIRONMENTAL OBSERVATIONS (Phase 3 Core Tables)
# =====================================================================

class AirQualityObservation(Base):
    """
    Air Quality observation entity. Stores timestamped telemetry with duplicate prevention.
    """
    __tablename__ = "air_quality_observations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # Telemetry observation time
    created_at = Column(DateTime, default=utc_now, nullable=False)  # Database insertion time
    aqi = Column(Float, nullable=True)
    pm2_5 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    source = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("region_id", "timestamp", "source", name="uq_air_quality_obs"),
        Index("idx_aq_region_time", "region_id", "timestamp"),
    )

    region = relationship("Region", back_populates="air_quality_records")

    def to_dict(self):
        return {
            "id": self.id,
            "region_id": self.region_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "aqi": self.aqi,
            "pm25": self.pm2_5,
            "pm10": self.pm10,
            "co": self.co,
            "no2": self.no2,
            "so2": self.so2,
            "o3": self.o3,
            "source": self.source
        }


class WeatherObservation(Base):
    """
    Weather observation entity. Stores meteorological variables with duplicate prevention.
    """
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # Telemetry observation time
    created_at = Column(DateTime, default=utc_now, nullable=False)  # Database insertion time
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)
    source = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("region_id", "timestamp", "source", name="uq_weather_obs"),
        Index("idx_weather_region_time", "region_id", "timestamp"),
    )

    region = relationship("Region", back_populates="weather_records")

    def to_dict(self):
        return {
            "id": self.id,
            "region_id": self.region_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "pressure": self.pressure,
            "rainfall": self.rainfall,
            "source": self.source
        }


class Prediction(Base):
    """
    ML Prediction entity. Populated in future Phase 4+ (Prediction models).
    """
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    prediction_time = Column(DateTime, default=utc_now)
    forecast_time = Column(DateTime, nullable=False)
    predicted_aqi = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False)

    region = relationship("Region", back_populates="predictions")


class Anomaly(Base):
    """
    Pollution spike/anomaly detection record. Populated in future Phase 5+.
    """
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=utc_now)
    pollutant = Column(String(50), nullable=False)
    observed_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    severity = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL

    region = relationship("Region", back_populates="anomalies")

    def to_dict(self):
        return {
            "id": self.id,
            "region_id": self.region_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "pollutant": self.pollutant,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "anomaly_score": self.anomaly_score,
            "severity": self.severity
        }


class HotspotResult(Base):
    """
    Pollution Hotspot assessment record (Phase 5).
    """
    __tablename__ = "hotspot_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    hotspot_score = Column(Float, nullable=False)
    level = Column(String(30), nullable=False)  # NORMAL, ELEVATED, HOTSPOT, SEVERE HOTSPOT
    aqi = Column(Float, nullable=False)
    method_version = Column(String(50), default="v1.0")

    region = relationship("Region", back_populates="hotspot_results")

    def to_dict(self):
        return {
            "id": self.id,
            "region_id": self.region_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "hotspot_score": self.hotspot_score,
            "level": self.level,
            "aqi": self.aqi,
            "method_version": self.method_version
        }


class Alert(Base):
    """
    Alert notification entity (Phase 6 Intelligent Alerts).
    Supports deduplication, cooldown, escalation, and lifecycle tracking.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    alert_type = Column(String(50), nullable=False, index=True)  # Trigger type (HIGH_RISK, POLLUTION_ANOMALY, etc.)
    title = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(20), default="UNREAD", index=True)  # UNREAD, READ, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=utc_now)
    read_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    dedupe_key = Column(String(150), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)

    region = relationship("Region", back_populates="alerts")

    def to_dict(self):
        region_name = self.region.name if self.region else None
        return {
            "id": self.id,
            "region_id": self.region_id,
            "region": region_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else (self.timestamp.isoformat() if self.timestamp else None),
            "trigger_type": self.alert_type,
            "alert_type": self.alert_type,
            "title": self.title or self.alert_type.replace("_", " ").title(),
            "message": self.message,
            "severity": self.severity,
            "status": self.status,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "dedupe_key": self.dedupe_key
        }

