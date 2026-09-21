import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque

from stream_engine.config import settings
from stream_engine.simulator import TelemetrySimulator
from stream_engine.models.yield_forecaster import RenewableYieldForecaster
from stream_engine.models.anomaly_detector import InverterAnomalyDetector
from stream_engine.models.dispatch_optimizer import BatteryDispatchOptimizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("StreamWorker")

class StreamWorker:
    """
    High-Throughput IoT Stream Processing Engine.
    Executes real-time LightGBM/XGBoost inference, string anomaly detection,
    and battery dispatch optimization directly in the 2-second streaming path.
    """
    def __init__(self):
        self.simulator = TelemetrySimulator()
        self.forecaster = RenewableYieldForecaster(
            solar_capacity_kw=settings.PLANT.solar_capacity_mw * 1000.0,
            wind_capacity_kw=settings.PLANT.wind_capacity_mw * 1000.0
        )
        self.anomaly_detector = InverterAnomalyDetector()
        self.dispatch_optimizer = BatteryDispatchOptimizer(
            capacity_kwh=settings.PLANT.bess_capacity_mwh * 1000.0,
            max_power_kw=settings.PLANT.bess_max_power_mw * 1000.0,
            penalty_rate_usd_kwh=settings.PLANT.penalty_rate_per_kwh
        )
        
        # In-memory sliding windows for real-time visualization
        self.recent_telemetry = deque(maxlen=120)       # Last 4 minutes of 2s packets
        self.recent_forecasts = deque(maxlen=96)        # Rolling 15-minute forecasts
        self.recent_rollups_15m = deque(maxlen=96)      # Last 24 hours of 15m aggregates
        self.active_alerts: List[Dict[str, Any]] = []
        self.alert_history = deque(maxlen=200)
        
        # State tracking
        self.current_soc_pct = settings.PLANT.bess_initial_soc_pct
        self.total_energy_kwh = 0.0
        self.total_penalties_usd = 0.0
        self.total_savings_usd = 0.0
        self.total_revenue_usd = 0.0
        self.last_packet: Optional[Dict[str, Any]] = None
        
        # 15-minute accumulator for continuous rollups
        self._15m_accumulator = {
            "start_time": datetime.now(),
            "power_samples": [],
            "irradiance_samples": [],
            "wind_samples": []
        }
        
        self.is_running = False

    def process_telemetry_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single 2-second telemetry packet synchronously through the ML/analytics pipeline.
        """
        now = datetime.fromisoformat(packet["timestamp"])
        weather = packet["weather"]
        renewable_kw = packet["total_renewable_kw"]
        committed_kw = packet["committed_schedule_kw"]
        tariff_usd = packet["tariff_usd_kwh"]
        
        # 1. Real-time 15-Minute ML Rolling Yield Forecast
        # Check if any inverters are in fault to adjust active ratio
        active_inverters = [inv for inv in packet["inverters"] if inv["status"] != "FAULT"]
        active_ratio = len(active_inverters) / max(1, len(packet["inverters"]))
        
        forecast = self.forecaster.predict_15m_rolling(
            current_time=now,
            irradiance_wm2=weather["irradiance_wm2"],
            ambient_temp_c=weather["ambient_temp_c"],
            wind_speed_ms=weather["wind_speed_ms"],
            active_inverter_ratio=active_ratio
        )
        
        # 2. Battery Dispatch Optimization (Penalty avoidance + Tariff Arbitrage + P90 Risk Assessment)
        dispatch_res = self.dispatch_optimizer.optimize_dispatch(
            renewable_gen_kw=renewable_kw,
            forecast_15m_kw=forecast["predicted_total_kw"],
            committed_schedule_kw=committed_kw,
            current_soc_pct=self.current_soc_pct,
            tariff_usd_kwh=tariff_usd,
            deadband_pct=settings.PLANT.schedule_deadband_pct,
            time_step_hours=settings.TELEMETRY_INTERVAL_SEC / 3600.0,
            p90_conservative_kw=forecast.get("p90_conservative_kw", 0.0),
            p10_optimistic_kw=forecast.get("p10_optimistic_kw", 0.0)
        )
        self.current_soc_pct = dispatch_res["updated_soc_pct"]
        
        # Accumulate financial metrics
        step_hours = settings.TELEMETRY_INTERVAL_SEC / 3600.0
        self.total_penalties_usd += dispatch_res["penalty_cost_rate_usd_h"] * step_hours
        self.total_savings_usd += dispatch_res["penalty_avoided_usd_h"] * step_hours
        self.total_revenue_usd += dispatch_res["revenue_rate_usd_h"] * step_hours
        self.total_energy_kwh += (dispatch_res["final_injected_kw"] * step_hours)
        
        # 3. Anomaly & String Health Detection
        new_alerts = []
        for inv in packet["inverters"]:
            inv_alerts = self.anomaly_detector.evaluate_inverter_strings(
                plant_id=packet["plant_id"],
                inverter_id=inv["inverter_id"],
                strings_data=inv["strings"],
                inverter_temp_c=inv["inverter_temp_c"],
                timestamp=now
            )
            new_alerts.extend(inv_alerts)
            
        # Grid schedule compliance alert
        grid_alerts = self.anomaly_detector.evaluate_grid_compliance(
            plant_id=packet["plant_id"],
            actual_injected_kw=dispatch_res["final_injected_kw"],
            committed_schedule_kw=committed_kw,
            tolerance_pct=settings.PLANT.schedule_deadband_pct,
            bess_available_dispatch_kw=dispatch_res["available_discharge_kw"],
            timestamp=now
        )
        new_alerts.extend(grid_alerts)
        
        # Manage alert state
        self.active_alerts = new_alerts
        for alert in new_alerts:
            # Avoid duplicate flooding in history
            if not any(a["alert_type"] == alert["alert_type"] and a.get("string_id") == alert.get("string_id") and a.get("inverter_id") == alert.get("inverter_id") for a in list(self.alert_history)[-10:]):
                self.alert_history.append(alert)

        # 4. Downsampling & Rollup Accumulation (15m hypertable aggregates)
        self._15m_accumulator["power_samples"].append(dispatch_res["final_injected_kw"])
        self._15m_accumulator["irradiance_samples"].append(weather["irradiance_wm2"])
        self._15m_accumulator["wind_samples"].append(weather["wind_speed_ms"])
        
        if (now - self._15m_accumulator["start_time"]).total_seconds() >= 900: # 15 mins
            powers = self._15m_accumulator["power_samples"]
            irrs = self._15m_accumulator["irradiance_samples"]
            winds = self._15m_accumulator["wind_samples"]
            
            rollup = {
                "bucket": self._15m_accumulator["start_time"].isoformat(),
                "avg_power_kw": round(sum(powers) / len(powers), 2) if powers else 0.0,
                "max_power_kw": round(max(powers), 2) if powers else 0.0,
                "min_power_kw": round(min(powers), 2) if powers else 0.0,
                "avg_irradiance": round(sum(irrs) / len(irrs), 2) if irrs else 0.0,
                "avg_wind_speed": round(sum(winds) / len(winds), 2) if winds else 0.0,
                "energy_kwh": round(sum(powers) * (settings.TELEMETRY_INTERVAL_SEC / 3600.0), 2)
            }
            self.recent_rollups_15m.append(rollup)
            self._15m_accumulator = {
                "start_time": now,
                "power_samples": [],
                "irradiance_samples": [],
                "wind_samples": []
            }

        # 5. Build enriched stream packet
        enriched = {
            **packet,
            "forecast_15m": forecast,
            "bess_dispatch": dispatch_res,
            "bess_soc_pct": self.current_soc_pct,
            "active_alerts": self.active_alerts,
            "financial_kpis": {
                "total_penalties_usd": round(self.total_penalties_usd, 2),
                "total_savings_usd": round(self.total_savings_usd, 2),
                "total_revenue_usd": round(self.total_revenue_usd, 2),
                "total_energy_mwh": round(self.total_energy_kwh / 1000.0, 3)
            }
        }
        
        self.recent_telemetry.append(enriched)
        self.recent_forecasts.append(forecast)
        self.last_packet = enriched
        return enriched

    async def run_loop(self):
        """Asynchronous stream execution loop generating and processing packets every 2 seconds."""
        self.is_running = True
        logger.info("Starting High-Throughput Stream Ingestion & Inference Loop...")
        
        while self.is_running:
            try:
                packet = self.simulator.generate_packet()
                self.process_telemetry_packet(packet)
            except Exception as e:
                logger.error(f"Error in stream processing step: {e}", exc_info=True)
                
            await asyncio.sleep(settings.TELEMETRY_INTERVAL_SEC)

    def stop(self):
        self.is_running = False

# Global worker instance
worker = StreamWorker()
