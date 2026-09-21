-- Enable TimescaleDB extension if available
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Raw 2-second IoT Telemetry
CREATE TABLE IF NOT EXISTS raw_telemetry (
    time TIMESTAMPTZ NOT NULL,
    plant_id VARCHAR(50) NOT NULL,
    inverter_id VARCHAR(50) NOT NULL,
    string_id VARCHAR(50),
    voltage_v DOUBLE PRECISION NOT NULL,
    current_a DOUBLE PRECISION NOT NULL,
    power_kw DOUBLE PRECISION NOT NULL,
    irradiance_wm2 DOUBLE PRECISION,
    wind_speed_ms DOUBLE PRECISION,
    ambient_temp_c DOUBLE PRECISION,
    module_temp_c DOUBLE PRECISION,
    inverter_temp_c DOUBLE PRECISION,
    grid_freq_hz DOUBLE PRECISION DEFAULT 50.0,
    grid_voltage_v DOUBLE PRECISION DEFAULT 400.0,
    status VARCHAR(20) DEFAULT 'NORMAL',
    PRIMARY KEY (time, plant_id, inverter_id, string_id)
);

-- Convert to Hypertable if timescaledb is loaded
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('raw_telemetry', 'time', if_not_exists => TRUE);
    END IF;
END $$;

-- Indexes for time-series queries
CREATE INDEX IF NOT EXISTS idx_telemetry_plant_time ON raw_telemetry (plant_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_inverter_time ON raw_telemetry (inverter_id, time DESC);

-- 2. 15-Minute Downsampled Aggregates
CREATE TABLE IF NOT EXISTS telemetry_15m (
    bucket TIMESTAMPTZ NOT NULL,
    plant_id VARCHAR(50) NOT NULL,
    inverter_id VARCHAR(50) NOT NULL,
    avg_power_kw DOUBLE PRECISION NOT NULL,
    max_power_kw DOUBLE PRECISION NOT NULL,
    min_power_kw DOUBLE PRECISION NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    avg_wind_speed DOUBLE PRECISION,
    avg_module_temp DOUBLE PRECISION,
    avg_voltage DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION,
    PRIMARY KEY (bucket, plant_id, inverter_id)
);

-- 3. 1-Hour Downsampled Aggregates
CREATE TABLE IF NOT EXISTS telemetry_1h (
    bucket TIMESTAMPTZ NOT NULL,
    plant_id VARCHAR(50) NOT NULL,
    inverter_id VARCHAR(50) NOT NULL,
    avg_power_kw DOUBLE PRECISION NOT NULL,
    max_power_kw DOUBLE PRECISION NOT NULL,
    min_power_kw DOUBLE PRECISION NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    avg_wind_speed DOUBLE PRECISION,
    total_energy_kwh DOUBLE PRECISION,
    PRIMARY KEY (bucket, plant_id, inverter_id)
);

-- 4. 15-Minute Rolling Generation Forecasts
CREATE TABLE IF NOT EXISTS generation_forecasts (
    id BIGSERIAL PRIMARY KEY,
    forecast_generated_at TIMESTAMPTZ NOT NULL,
    target_time TIMESTAMPTZ NOT NULL,
    plant_id VARCHAR(50) NOT NULL,
    predicted_solar_kw DOUBLE PRECISION NOT NULL,
    predicted_wind_kw DOUBLE PRECISION NOT NULL,
    predicted_total_kw DOUBLE PRECISION NOT NULL,
    lower_bound_kw DOUBLE PRECISION,
    upper_bound_kw DOUBLE PRECISION,
    confidence_score DOUBLE PRECISION DEFAULT 0.95,
    actual_power_kw DOUBLE PRECISION,
    committed_schedule_kw DOUBLE PRECISION,
    battery_dispatch_kw DOUBLE PRECISION DEFAULT 0.0,
    deviation_penalty DOUBLE PRECISION DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_forecast_target ON generation_forecasts (plant_id, target_time DESC);

-- 5. Inverter String Health & Anomaly Alerts
CREATE TABLE IF NOT EXISTS inverter_alerts (
    id BIGSERIAL PRIMARY KEY,
    plant_id VARCHAR(50) NOT NULL,
    inverter_id VARCHAR(50) NOT NULL,
    string_id VARCHAR(50),
    alert_type VARCHAR(50) NOT NULL, -- 'STRING_VOLTAGE_MISMATCH', 'INVERTER_OVERHEAT', 'BLOWN_FUSE', 'GRID_DEVIATION_RISK'
    severity VARCHAR(20) NOT NULL,   -- 'CRITICAL', 'WARNING', 'INFO'
    message TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'OPEN', -- 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_status ON inverter_alerts (status, detected_at DESC);
