-- =======================================================
-- AIRGUARD AI - Database Schema Reference (Phase 1)
-- =======================================================

-- 1. Regions Table
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Air Quality Observations (Phase 3 Historical Storage)
CREATE TABLE IF NOT EXISTS air_quality_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aqi FLOAT,
    pm2_5 FLOAT,
    pm10 FLOAT,
    co FLOAT,
    no2 FLOAT,
    so2 FLOAT,
    o3 FLOAT,
    source VARCHAR(100) NOT NULL,
    CONSTRAINT uq_air_quality_obs UNIQUE (region_id, timestamp, source)
);
CREATE INDEX IF NOT EXISTS idx_aq_region_time ON air_quality_observations(region_id, timestamp);

-- 3. Weather Observations (Phase 3 Historical Storage)
CREATE TABLE IF NOT EXISTS weather_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    wind_speed FLOAT,
    wind_direction FLOAT,
    pressure FLOAT,
    rainfall FLOAT,
    source VARCHAR(100) NOT NULL,
    CONSTRAINT uq_weather_obs UNIQUE (region_id, timestamp, source)
);
CREATE INDEX IF NOT EXISTS idx_weather_region_time ON weather_observations(region_id, timestamp);

-- 4. Predictions (Phase 4+)
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    forecast_time TIMESTAMP NOT NULL,
    predicted_aqi FLOAT NOT NULL,
    model_version VARCHAR(50) NOT NULL
);

-- 5. Anomalies (Phase 5+)
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pollutant VARCHAR(50) NOT NULL,
    observed_value FLOAT NOT NULL,
    expected_value FLOAT,
    anomaly_score FLOAT,
    severity VARCHAR(20) NOT NULL
);

-- 6. Alerts (Phase 6 Intelligent Alerts)
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'UNREAD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    dedupe_key VARCHAR(150),
    expires_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alerts_region ON alerts(region_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_dedupe ON alerts(dedupe_key);

