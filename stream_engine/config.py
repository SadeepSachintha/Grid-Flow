import os
from pydantic import BaseModel

class PlantConfig(BaseModel):
    plant_id: str = "PLANT-SOLARIA-01"
    name: str = "Solaria West Microgrid & Wind Farm"
    solar_capacity_mw: float = 20.0
    wind_capacity_mw: float = 5.0
    total_capacity_mw: float = 25.0
    latitude: float = 34.924
    longitude: float = -116.892
    
    # Inverters: 4 Central Inverters (5MW each), 8 strings each = 32 strings
    inverters: list = ["INV-01", "INV-02", "INV-03", "INV-04"]
    strings_per_inverter: int = 8
    nominal_string_voltage_v: float = 850.0  # 1500V DC bus architecture
    nominal_string_current_a: float = 18.5
    
    # Wind Turbines: 2x 2.5MW
    turbines: list = ["WTG-01", "WTG-02"]
    
    # BESS: 10MWh, 5MW max discharge/charge
    bess_id: str = "BESS-01"
    bess_capacity_mwh: float = 10.0
    bess_max_power_mw: float = 5.0
    bess_initial_soc_pct: float = 65.0
    
    # Grid contract parameters
    schedule_deadband_pct: float = 5.0       # +/- 5% tolerance
    penalty_rate_per_kwh: float = 0.075      # $75/MWh penalty for shortfall or excess

class Settings:
    # Service Endpoints
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    
    # Message Brokers
    MQTT_HOST: str = os.getenv("MQTT_HOST", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_TOPIC_TELEMETRY: str = "gridflow/telemetry/raw"
    MQTT_TOPIC_ALERTS: str = "gridflow/alerts"
    
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_TELEMETRY: str = "gridflow-telemetry"
    
    # Database
    TIMESCALE_URL: str = os.getenv(
        "TIMESCALE_URL", 
        "postgresql://gridflow:gridflow_secret@localhost:5432/gridflow_ts"
    )
    SQLITE_PATH: str = os.path.join(os.path.dirname(__file__), "gridflow_local.db")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # Simulation frequency
    TELEMETRY_INTERVAL_SEC: float = 2.0
    
    # Plant Configuration
    PLANT: PlantConfig = PlantConfig()

settings = Settings()
