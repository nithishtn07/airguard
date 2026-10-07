import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Centralized Configuration for AirGuard AI.
    Loads values from environment variables or .env file.
    """
    APP_NAME: str = "AirGuard AI"
    APP_VERSION: str = "9.0.0-phase9"
    PHASE: int = 9
    ENVIRONMENT: str = Field(default="development", description="Current environment: development, testing, or production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    # Phase 9: User-Selected Location & Custom Time-Window Analysis Settings
    GEOCODING_API_KEY: str = Field(default="", description="Optional API key for external geocoding providers")
    GEOCODING_PROVIDER: str = Field(default="openmeteo_nominatim", description="Primary geocoding provider")
    MAX_CUSTOM_RANGE_DAYS: int = Field(default=365, description="Maximum allowable custom date range in days")

    # Machine Learning Settings (Phase 4)
    MIN_TRAINING_ROWS: int = Field(default=30, description="Minimum historical observations required to train model")
    MODELS_DIR: str = Field(default="./ml/models", description="Directory to persist trained ML model artifacts")
    DEFAULT_MODEL_TYPE: str = Field(default="RandomForestRegressor", description="Primary model architecture")
    RANDOM_SEED: int = Field(default=42, description="Random seed for model training and splitting reproducibility")

    # Phase 5: Hotspot & Anomaly Detection Settings
    ANOMALY_METHOD: str = Field(default="zscore", description="Statistical anomaly detection method (zscore, iqr)")
    ANOMALY_Z_THRESHOLD: float = Field(default=2.5, description="Z-score threshold for flagging an observation as anomalous")
    ANOMALY_ROLLING_WINDOW: int = Field(default=24, description="Rolling window size in hours for computing dynamic anomaly baselines")
    MIN_ANOMALY_OBSERVATIONS: int = Field(default=12, description="Minimum historical observations required for anomaly evaluation")
    HOTSPOT_SCORE_THRESHOLD: float = Field(default=0.60, description="Hotspot score threshold (0.0 to 1.0) for HOTSPOT classification")
    HOTSPOT_HISTORY_HOURS: int = Field(default=24, description="Hours of past telemetry used to assess hotspot persistence and baseline")
    MIN_HOTSPOT_OBSERVATIONS: int = Field(default=6, description="Minimum historical observations required for regional hotspot audit")

    # Phase 6: Risk Assessment, Recommendations & Alerts Settings
    RISK_MODEL: str = Field(default="composite_v1", description="Risk assessment scoring model version")
    RISK_LOW_MAX: float = Field(default=25.0, description="Upper threshold for LOW risk category (0 to 25)")
    RISK_MODERATE_MAX: float = Field(default=50.0, description="Upper threshold for MODERATE risk category (25 to 50)")
    RISK_HIGH_MAX: float = Field(default=75.0, description="Upper threshold for HIGH risk category (50 to 75)")
    RISK_VERY_HIGH_MAX: float = Field(default=90.0, description="Upper threshold for VERY HIGH risk category (75 to 90), >90 is CRITICAL")

    ALERT_COOLDOWN_MINUTES: int = Field(default=60, description="Minutes before duplicate condition triggers a new alert")
    ALERT_DEDUPLICATION_ENABLED: bool = Field(default=True, description="Enable deduplication of active environmental alerts")
    HIGH_RISK_ALERT_ENABLED: bool = Field(default=True, description="Enable alerts for HIGH/CRITICAL risk levels")
    ANOMALY_ALERT_ENABLED: bool = Field(default=True, description="Enable alerts for detected pollution anomalies")
    HOTSPOT_ALERT_ENABLED: bool = Field(default=True, description="Enable alerts for pollution hotspots")
    PREDICTION_ALERT_ENABLED: bool = Field(default=True, description="Enable alerts for forecasted pollution deterioration")

    # Server settings
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Database settings (Defaults to local SQLite)
    DATABASE_URL: str = Field(
        default="sqlite:///./data/airguard.db",
        description="SQLAlchemy database connection URI"
    )

    # API Keys & Endpoints (Phase 2 Data Providers)
    AIR_QUALITY_API_KEY: str = Field(default="", description="Phase 2: Live Air Quality API Key (Optional for Open-Meteo)")
    WEATHER_API_KEY: str = Field(default="", description="Phase 2: Live Weather API Key (Optional for Open-Meteo)")
    GEMINI_API_KEY: str = Field(default="", description="Phase 6+: Generative AI Key")

    # External API Request Settings
    EXTERNAL_API_TIMEOUT_SECONDS: float = Field(default=10.0, description="Timeout for external API calls")
    CACHE_TTL_SECONDS: int = Field(default=60, description="Short-lived cache TTL for live API responses")

    # CORS origins
    CORS_ORIGINS: List[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


# Singleton instance
settings = Settings()
