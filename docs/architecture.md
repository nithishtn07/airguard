# AirGuard AI — System Architecture & Design Specification

## Overview

**AirGuard AI** is a real-time air quality monitoring and predictive intelligence platform designed for user-selected regions. The platform ingests atmospheric pollutant telemetry and meteorological variables, stores historical trends, applies machine learning models to forecast future Air Quality Index (AQI) values, flags abnormal spikes and hotspots, and presents actionable recommendations.

---

## Architectural Workflow

```mermaid
flowchart TD
    User([User]) -->|Selects Region| WebUI[Web Dashboard]
    
    subgraph Data Layer [Phase 2]
        AQ_API[Air Quality Telemetry]
        Weather_API[Meteorological Telemetry]
        Sensors[IoT Sensors Optional]
    end

    subgraph Storage [Phase 1 & Onward]
        DB[(Relational DB / SQLite)]
    end

    subgraph Pipeline [Phase 3]
        Validator[Data Validator & Sanitizer]
        Cleaner[Preprocessing & Missing Value Imputation]
        Features[Feature Engineering & Temporal Encoders]
    end

    subgraph ML Intelligence [Phase 4-5]
        Predictor[ML AQI Forecaster]
        AnomalyDetector[Pollution Spike & Anomaly Detector]
        HotspotDetector[Spatial Hotspot Engine]
    end

    subgraph Decision Engine [Phase 6]
        RiskClassifier[AQI Risk Categorizer]
        Advisor[Smart Recommendations Engine]
        Alerts[Alert Dispatcher]
    end

    AQ_API --> Validator
    Weather_API --> Validator
    Sensors --> Validator
    Validator --> DB
    DB --> Cleaner --> Features --> Predictor
    Features --> AnomalyDetector
    Features --> HotspotDetector
    Predictor --> RiskClassifier
    AnomalyDetector --> Alerts
    RiskClassifier --> Advisor
    Advisor --> WebUI
    Alerts --> WebUI
    Predictor --> WebUI
    DB --> WebUI
```

---

## Relational Entity Model (Phase 1 Foundation)

```mermaid
erDiagram
    REGION ||--o{ AIR_QUALITY_OBSERVATION : records
    REGION ||--o{ WEATHER_OBSERVATION : records
    REGION ||--o{ PREDICTION : generates
    REGION ||--o{ ANOMALY : flags
    REGION ||--o{ ALERT : triggers

    REGION {
        int id PK
        string name UK
        float latitude
        float longitude
        string state
        string country
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    AIR_QUALITY_OBSERVATION {
        int id PK
        int region_id FK
        datetime timestamp
        float aqi
        float pm2_5
        float pm10
        float co
        float no2
        float so2
        float o3
        string source
    }

    WEATHER_OBSERVATION {
        int id PK
        int region_id FK
        datetime timestamp
        float temperature
        float humidity
        float wind_speed
        float wind_direction
        float pressure
        float rainfall
    }

    PREDICTION {
        int id PK
        int region_id FK
        datetime prediction_time
        datetime forecast_time
        float predicted_aqi
        string model_version
    }

    ANOMALY {
        int id PK
        int region_id FK
        datetime timestamp
        string pollutant
        float observed_value
        float expected_value
        float anomaly_score
        string severity
    }

    ALERT {
        int id PK
        int region_id FK
        datetime timestamp
        string alert_type
        string message
        string severity
        string status
    }
```

---

## Modular Directory Map

```text
airqualitymodel/
├── backend/
│   ├── main.py                  # Application entry point, lifespan, CORS, error handling
│   ├── routes/
│   │   ├── health.py            # /api/health endpoint
│   │   └── regions.py           # /api/regions, /api/regions/{id} endpoints
│   ├── services/
│   │   ├── region_service.py    # Region database operations & seeding
│   │   └── data_collector.py    # Architectural interface for Phase 2 data collectors
│   ├── models/
│   │   ├── models.py            # SQLAlchemy ORM models (Region & future entities)
│   │   └── schemas.py           # Pydantic schemas for data validation
│   └── utils/
│       └── logger.py            # Standardized application logging
├── config/
│   └── settings.py              # Centralized environment configuration (Pydantic Settings)
├── database/
│   ├── session.py               # Engine & sessionmaker configuration
│   └── schema/schema.sql        # Standalone SQL DDL reference
├── docs/
│   └── architecture.md          # Architecture and entity documentation
├── frontend/
│   ├── index.html               # Main dashboard UI
│   ├── components/app.js        # Frontend client logic & API bindings
│   └── styles/index.css         # Modern, responsive design system
├── ml/
│   ├── preprocessing/preprocessor.py # Phase 3 contract
│   └── prediction/predictor.py       # Phase 4 contract
├── tests/
│   └── test_phase1.py           # Comprehensive Phase 1 test suite
├── .env.example                 # Environment configuration template
├── .gitignore                   # Version control exclusion rules
├── requirements.txt             # Dependency specifications
└── README.md                    # Project documentation
```
