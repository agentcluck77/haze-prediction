-- Database initialization script
-- Creates necessary tables and indexes for haze prediction system

-- Fire detections
CREATE TABLE IF NOT EXISTS fire_detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    frp DECIMAL(10, 2),
    brightness DECIMAL(10, 2),
    confidence VARCHAR(10),
    acq_date DATE,
    acq_time VARCHAR(10),
    satellite VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timestamp, latitude, longitude)
);

CREATE INDEX IF NOT EXISTS idx_fire_timestamp ON fire_detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_fire_location ON fire_detections(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_fire_created_at ON fire_detections(created_at);

-- Weather data
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    location VARCHAR(100),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    timestamp TIMESTAMP NOT NULL,
    temperature_2m DECIMAL(5, 2),
    relative_humidity_2m DECIMAL(5, 2),
    wind_speed_10m DECIMAL(5, 2),
    wind_direction_10m DECIMAL(5, 2),
    wind_gusts_10m DECIMAL(5, 2),
    pressure_msl DECIMAL(7, 2),
    is_forecast BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(location, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_weather_timestamp ON weather_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_weather_location ON weather_data(location, timestamp);
CREATE INDEX IF NOT EXISTS idx_weather_created_at ON weather_data(created_at);

-- PSI readings
CREATE TABLE IF NOT EXISTS psi_readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    region VARCHAR(20),
    psi_24h INTEGER,
    pm25_24h INTEGER,
    pm10_24h INTEGER,
    o3_sub_index INTEGER,
    co_sub_index INTEGER,
    no2_1h_max INTEGER,
    so2_24h INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timestamp, region)
);

CREATE INDEX IF NOT EXISTS idx_psi_timestamp ON psi_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_psi_region ON psi_readings(region, timestamp);
CREATE INDEX IF NOT EXISTS idx_psi_created_at ON psi_readings(created_at);

-- Predictions (for validation tracking)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    target_timestamp TIMESTAMP NOT NULL,
    horizon VARCHAR(10) NOT NULL,
    predicted_psi DECIMAL(6, 2) NOT NULL,
    confidence_lower DECIMAL(6, 2),
    confidence_upper DECIMAL(6, 2),
    fire_risk_score DECIMAL(5, 2),
    wind_transport_score DECIMAL(5, 2),
    baseline_score DECIMAL(5, 2),
    model_version VARCHAR(50) DEFAULT 'phase1_linear',
    actual_psi DECIMAL(6, 2),
    absolute_error DECIMAL(6, 2),
    squared_error DECIMAL(8, 2),
    validated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_target ON predictions(target_timestamp, horizon);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_validation ON predictions(validated_at);

-- Validation metrics (aggregated performance)
CREATE TABLE IF NOT EXISTS validation_metrics (
    id SERIAL PRIMARY KEY,
    horizon VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    sample_count INTEGER NOT NULL,
    mae DECIMAL(6, 2),
    rmse DECIMAL(6, 2),
    alert_precision DECIMAL(5, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(horizon, date)
);

CREATE INDEX IF NOT EXISTS idx_validation_horizon ON validation_metrics(horizon, date);

-- System health logs
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    service VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_health_timestamp ON system_health(timestamp);
CREATE INDEX IF NOT EXISTS idx_health_service ON system_health(service, timestamp);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hazeuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hazeuser;
