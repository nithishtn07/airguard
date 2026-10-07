from backend.services.region_service import (
    init_db_and_seed,
    get_all_regions,
    get_region_by_id,
    get_region_by_name,
    get_region_by_identifier,
    create_region
)
from backend.services.air_quality_service import fetch_live_air_quality
from backend.services.weather_service import fetch_live_weather
from backend.services.data_collector import collector, BaseDataCollector, OpenMeteoDataCollector
from backend.services.storage_service import (
    save_air_quality_observation,
    save_weather_observation,
    save_environmental_snapshot,
    get_historical_observations,
    get_database_stats
)
from backend.services.preprocessing_service import (
    analyze_data_quality,
    prepare_ml_dataset,
    validate_physical_bounds,
    detect_outliers_iqr,
    handle_missing_values,
    engineer_temporal_features
)

from backend.services.hotspot_service import (
    assess_hotspots,
    evaluate_region_hotspot,
    get_regional_hotspot_detail
)
from backend.services.anomaly_service import (
    detect_anomalies_for_region,
    assess_all_anomalies
)
from backend.services.risk_service import (
    assess_environmental_risk,
    calculate_risk_level_and_color
)
from backend.services.recommendation_service import generate_recommendations
from backend.services.alert_service import (
    evaluate_and_dispatch_alerts,
    get_alerts_for_region,
    get_all_alerts,
    mark_alert_read,
    acknowledge_alert,
    resolve_alert
)

from backend.services.geocoding_service import geocoding_service
from backend.services.environmental_information_service import environmental_information_service
from backend.services.best_practices_service import best_practices_service
from backend.services.insights_analysis_service import insights_analysis_service

__all__ = [
    "init_db_and_seed",
    "get_all_regions",
    "get_region_by_id",
    "get_region_by_name",
    "get_region_by_identifier",
    "create_region",
    "fetch_live_air_quality",
    "fetch_live_weather",
    "collector",
    "BaseDataCollector",
    "OpenMeteoDataCollector",
    "save_air_quality_observation",
    "save_weather_observation",
    "save_environmental_snapshot",
    "get_historical_observations",
    "get_database_stats",
    "analyze_data_quality",
    "prepare_ml_dataset",
    "validate_physical_bounds",
    "detect_outliers_iqr",
    "handle_missing_values",
    "engineer_temporal_features",
    "assess_hotspots",
    "evaluate_region_hotspot",
    "get_regional_hotspot_detail",
    "detect_anomalies_for_region",
    "assess_all_anomalies",
    "assess_environmental_risk",
    "calculate_risk_level_and_color",
    "generate_recommendations",
    "evaluate_and_dispatch_alerts",
    "get_alerts_for_region",
    "get_all_alerts",
    "mark_alert_read",
    "acknowledge_alert",
    "resolve_alert",
    "geocoding_service",
    "environmental_information_service",
    "best_practices_service",
    "insights_analysis_service",
]

