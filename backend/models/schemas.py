from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RegionBase(BaseModel):
    name: str = Field(..., description="Region name (e.g. Chennai, Bangalore)", example="Chennai")
    latitude: float = Field(..., description="Latitude coordinate", example=13.0827)
    longitude: float = Field(..., description="Longitude coordinate", example=80.2707)
    state: Optional[str] = Field(None, description="State / Province", example="Tamil Nadu")
    country: str = Field(default="India", description="Country name", example="India")
    is_active: bool = Field(default=True, description="Whether monitoring is enabled for this region")


class RegionCreate(RegionBase):
    pass


class RegionResponse(RegionBase):
    id: int = Field(..., description="Unique identifier for the region")
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    application: str = Field(..., example="AirGuard AI")
    phase: int = Field(..., example=3)
    environment: str = Field(..., example="development")
    database_connected: bool = Field(..., example=True)
    timestamp: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# =====================================================================
# PHASE 2 SCHEMAS: AIR QUALITY & WEATHER DATA
# =====================================================================

class AirQualityData(BaseModel):
    region: str = Field(..., description="Name of the monitored region", example="Chennai")
    region_id: Optional[int] = Field(None, description="Database ID of the region")
    timestamp: str = Field(..., description="UTC ISO-8601 observation timestamp")
    aqi: Optional[float] = Field(None, description="Air Quality Index value (US/European standard)")
    pm25: Optional[float] = Field(None, description="Particulate Matter 2.5 in µg/m³")
    pm10: Optional[float] = Field(None, description="Particulate Matter 10 in µg/m³")
    co: Optional[float] = Field(None, description="Carbon Monoxide in µg/m³")
    no2: Optional[float] = Field(None, description="Nitrogen Dioxide in µg/m³")
    so2: Optional[float] = Field(None, description="Sulphur Dioxide in µg/m³")
    o3: Optional[float] = Field(None, description="Ozone in µg/m³")
    source: str = Field(..., description="Data provider name")


class WeatherData(BaseModel):
    region: str = Field(..., description="Name of the monitored region", example="Chennai")
    region_id: Optional[int] = Field(None, description="Database ID of the region")
    timestamp: str = Field(..., description="UTC ISO-8601 observation timestamp")
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    humidity: Optional[float] = Field(None, description="Relative humidity percentage (0-100%)")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h")
    wind_direction: Optional[float] = Field(None, description="Wind direction in degrees (0-360°)")
    pressure: Optional[float] = Field(None, description="Atmospheric pressure in hPa")
    rainfall: Optional[float] = Field(None, description="Rainfall / precipitation in mm")
    source: str = Field(..., description="Data provider name")


class AirQualityResponse(BaseModel):
    success: bool = True
    data: AirQualityData
    source: str


class WeatherResponse(BaseModel):
    success: bool = True
    data: WeatherData
    source: str


class EnvironmentResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    timestamp: str
    air_quality: AirQualityData
    weather: WeatherData


# =====================================================================
# PHASE 3 SCHEMAS: HISTORICAL TELEMETRY & DATA QUALITY
# =====================================================================

class HistoricalObservationItem(BaseModel):
    timestamp: str
    created_at: Optional[str] = None
    aqi: Optional[float] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    co: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    o3: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    pressure: Optional[float] = None
    rainfall: Optional[float] = None
    aq_source: Optional[str] = None
    weather_source: Optional[str] = None


class HistoricalDataResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    range: str
    count: int
    observations: List[HistoricalObservationItem]


class DataQualitySummaryItem(BaseModel):
    missing_count: int
    missing_percentage: float
    present_count: int


class DataQualityResponse(BaseModel):
    success: bool = True
    region: str
    total_records: int
    time_range: Dict[str, Optional[str]]
    missing_summary: Dict[str, DataQualitySummaryItem]
    invalid_records_count: int
    duplicates_removed: int
    potential_outliers_count: int
    clean_records_count: int


# =====================================================================
# PHASE 4 SCHEMAS: MACHINE LEARNING & AQI PREDICTION
# =====================================================================

class PredictionDetail(BaseModel):
    target: str = Field(..., description="Prediction target identifier (e.g. next_step_aqi)", example="next_step_aqi")
    predicted_aqi: float = Field(..., description="Model forecasted Air Quality Index", example=118.5)
    current_aqi: Optional[float] = Field(None, description="Latest observed AQI for relative reference", example=112.0)
    trend: str = Field(..., description="Directional trend: INCREASING, DECREASING, or STABLE", example="INCREASING")
    trend_delta: Optional[float] = Field(None, description="Absolute difference between predicted and current AQI")
    confidence_bound_lower: Optional[float] = Field(None, description="Lower prediction bound (estimated uncertainty)", example=111.2)
    confidence_bound_upper: Optional[float] = Field(None, description="Upper prediction bound (estimated uncertainty)", example=125.8)
    uncertainty_spread: Optional[float] = Field(None, description="Ensemble prediction standard deviation spread")
    category: str = Field(..., description="Air quality health category for predicted AQI", example="Unhealthy for Sensitive Groups")
    category_color: str = Field(..., description="Hex or CSS color for category visual cue", example="#ff7e00")
    prediction_time: str = Field(..., description="UTC ISO timestamp when forecast was computed")
    forecast_time: str = Field(..., description="UTC ISO timestamp target horizon of forecast")
    model_type: str = Field(..., description="Architecture of the predictive model", example="RandomForestRegressor")
    model_version: str = Field(..., description="Identifier and timestamp of active trained model", example="airguard_rf_v1")


class PredictionResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    status: str = Field(..., description="Model status: 'available' or 'unavailable'", example="available")
    message: Optional[str] = None
    prediction: Optional[PredictionDetail] = None


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    description: Optional[str] = None


class ModelInfoResponse(BaseModel):
    success: bool = True
    model_available: bool
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    target: Optional[str] = None
    trained_at: Optional[str] = None
    training_rows: Optional[int] = 0
    validation_rows: Optional[int] = 0
    test_rows: Optional[int] = 0
    features: List[str] = []
    validation_metrics: Optional[Dict[str, float]] = None
    test_metrics: Optional[Dict[str, float]] = None
    top_features: List[FeatureImportanceItem] = []
    status_message: Optional[str] = None


class ModelTrainResponse(BaseModel):
    success: bool
    message: str
    report: Optional[Dict[str, Any]] = None


# =====================================================================
# PHASE 5 SCHEMAS: POLLUTION HOTSPOT & ANOMALY DETECTION
# =====================================================================

class HotspotComponentScores(BaseModel):
    aqi_severity: float = Field(..., description="Normalized severity of current AQI (0 to 1)")
    relative_deviation: float = Field(..., description="Deviation relative to other monitored regions (0 to 1)")
    historical_deviation: float = Field(..., description="Deviation relative to region's own 24h baseline (0 to 1)")
    persistence: float = Field(..., description="Fraction of recent observations in elevated territory (0 to 1)")


class HotspotRegionItem(BaseModel):
    rank: int = Field(..., description="Rank in hotspot hierarchy (1 = most severe)")
    region_id: int
    region: str
    latitude: float
    longitude: float
    current_aqi: float
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    hotspot_score: float = Field(..., description="Composite hotspot score (0.0 to 1.0)")
    level: str = Field(..., description="NORMAL, ELEVATED, HOTSPOT, or SEVERE HOTSPOT")
    level_color: str
    is_hotspot: bool
    components: HotspotComponentScores
    reasons: List[str] = []
    explanation: str
    observations_used: int


class HotspotResponse(BaseModel):
    success: bool = True
    generated_at: str
    range: str = "24h"
    total_regions_analyzed: int
    hotspots_count: int
    highest_hotspot_region: Optional[str] = None
    hotspots: List[HotspotRegionItem]


class AnomalyDetail(BaseModel):
    id: Optional[int] = None
    timestamp: str
    metric: str = Field(..., description="Pollutant or index (e.g. PM2.5, AQI, PM10)")
    observed_value: float
    expected_value: float
    baseline_std: float
    z_score: float
    anomaly_score: float = Field(..., description="Normalized anomaly score (0.0 to 1.0)")
    severity: str = Field(..., description="NORMAL, UNUSUAL, HIGH ANOMALY, or EXTREME ANOMALY")
    severity_color: str
    deviation: float
    reason: str


class AnomalyTimelinePoint(BaseModel):
    timestamp: str
    aqi: Optional[float] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    baseline_aqi: Optional[float] = None
    upper_bound_aqi: Optional[float] = None
    is_anomaly: bool = False
    anomaly_severity: Optional[str] = None


class AnomalyResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    latitude: float
    longitude: float
    generated_at: str
    method: str = "zscore"
    z_threshold: float
    observations_analyzed: int
    has_anomalies: bool
    anomaly_status: str = Field(..., description="Highest anomaly severity: NORMAL, UNUSUAL, HIGH ANOMALY, or EXTREME ANOMALY")
    highest_anomaly_score: float
    anomalies: List[AnomalyDetail] = []
    timeline: List[AnomalyTimelinePoint] = []


class CombinedIntelligenceResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    coordinates: Dict[str, float]
    generated_at: str
    current: Dict[str, Any]
    prediction: Optional[Dict[str, Any]] = None
    hotspot: Dict[str, Any]
    anomaly: Dict[str, Any]
    summary: str


# =====================================================================
# PHASE 6 SCHEMAS: RISK ASSESSMENT, RECOMMENDATIONS & INTELLIGENT ALERTS
# =====================================================================

class RiskContributors(BaseModel):
    current_aqi: float = Field(..., description="Current AQI component score (0-100)")
    predicted_aqi: Optional[float] = Field(None, description="Predicted AQI component score (0-100)")
    pollutants: Optional[float] = Field(None, description="Particulate toxicity component score (0-100)")
    hotspot: Optional[float] = Field(None, description="Hotspot severity component score (0-100)")
    anomaly: Optional[float] = Field(None, description="Anomaly deviation component score (0-100)")


class RiskAssessmentResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    timestamp: str
    risk_score: float = Field(..., description="Composite Environmental Risk Score (0.0 to 100.0)")
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, VERY HIGH, or CRITICAL")
    risk_color: str = Field(..., description="Hex color associated with risk level")
    confidence: Optional[float] = Field(None, description="Statistical confidence if available, else null")
    reasons: List[str] = Field(default=[], description="Explainable reasons supporting the risk score")
    contributors: Dict[str, Any] = Field(default={}, description="Score breakdown by component")
    data_available: bool = Field(True, description="Whether sufficient live telemetry exists")
    model_version: str = Field("composite_v1", description="Scoring methodology version")


class MultiRegionRiskResponse(BaseModel):
    success: bool = True
    generated_at: str
    total_regions: int
    regions: List[RiskAssessmentResponse]


class RecommendationItem(BaseModel):
    id: str
    priority: str = Field(..., description="HIGH, MEDIUM, or LOW")
    category: str = Field(..., description="OUTDOOR_ACTIVITY, EXPOSURE, MASK, TRAVEL, WEATHER, POLLUTION, ANOMALY, GENERAL")
    title: str
    message: str
    reason: str
    icon: Optional[str] = None


class RecommendationResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    generated_at: str
    risk_level: str
    risk_score: float
    data_available: bool = True
    total_recommendations: int
    recommendations: List[RecommendationItem] = []


class AlertItem(BaseModel):
    id: int
    region_id: int
    region: Optional[str] = None
    timestamp: str
    created_at: Optional[str] = None
    trigger_type: str = Field(..., description="Trigger reason (HIGH_RISK, POLLUTION_ANOMALY, etc.)")
    alert_type: str
    title: str
    message: str
    severity: str = Field(..., description="INFO, LOW, MEDIUM, HIGH, or CRITICAL")
    severity_color: Optional[str] = None
    status: str = Field(..., description="UNREAD, READ, ACKNOWLEDGED, or RESOLVED")
    read_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    dedupe_key: Optional[str] = None


class AlertListResponse(BaseModel):
    success: bool = True
    total_alerts: int
    unread_count: int
    region: Optional[str] = None
    alerts: List[AlertItem] = []


class AlertActionResponse(BaseModel):
    success: bool = True
    message: str
    alert: AlertItem


# =====================================================================
# PHASE 7 SCHEMAS: MAP DATA & UNIFIED DASHBOARD AGGREGATION
# =====================================================================

class MapRegionItem(BaseModel):
    region_id: int
    region: str
    latitude: float
    longitude: float
    state: Optional[str] = None
    country: str = "India"
    aqi: Optional[float] = None
    aqi_category: Optional[str] = None
    aqi_color: Optional[str] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_color: Optional[str] = None
    is_hotspot: bool = False
    hotspot_score: Optional[float] = None
    hotspot_severity: Optional[str] = None
    has_anomaly: bool = False
    latest_anomaly_metric: Optional[str] = None
    anomaly_severity: Optional[str] = None
    active_alerts_count: int = 0
    source: Optional[str] = None
    timestamp: Optional[str] = None
    updated_at: Optional[str] = None


class MapDataResponse(BaseModel):
    success: bool = True
    timestamp: str
    total_regions: int
    regions: List[MapRegionItem] = []


class DashboardAggregatedResponse(BaseModel):
    success: bool = True
    region: str
    region_id: int
    latitude: float
    longitude: float
    state: Optional[str] = None
    timestamp: str
    air_quality: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    prediction: Optional[Dict[str, Any]] = None
    hotspot: Optional[Dict[str, Any]] = None
    anomaly: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    unread_alerts_count: int = 0


