import math
from datetime import datetime, timedelta
from typing import Dict, List, Any
from stream_engine.config import settings
from stream_engine.models.yield_forecaster import RenewableYieldForecaster
from stream_engine.models.anomaly_detector import InverterAnomalyDetector
from stream_engine.models.dispatch_optimizer import BatteryDispatchOptimizer

class ScenarioArchive:
    """
    Industrial Incident Scenario Archive.
    Generates high-density, multi-minute frame sequences (2-second intervals)
    for recorded microgrid disturbance events.
    """
    def __init__(self):
        self.forecaster = RenewableYieldForecaster(
            solar_capacity_kw=settings.PLANT.solar_capacity_mw * 1000.0,
            wind_capacity_kw=settings.PLANT.wind_capacity_mw * 1000.0
        )
        self.anomaly_detector = InverterAnomalyDetector()
        self.dispatch_opt = BatteryDispatchOptimizer(
            capacity_kwh=settings.PLANT.bess_capacity_mwh * 1000.0,
            max_power_kw=settings.PLANT.bess_max_power_mw * 1000.0,
            penalty_rate_usd_kwh=settings.PLANT.penalty_rate_per_kwh
        )

    def get_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "INC-2026-041",
                "title": "Monsoonal Cloud Transit & Rapid BESS Discharge",
                "category": "WEATHER_DISTURBANCE",
                "duration_sec": 120,
                "frames_count": 60,
                "peak_sec": 44,
                "description": "Rapid 78% solar irradiance drop over 80 seconds. Demonstrates LightGBM quantile forecast reaction and automatic BESS deficit compensation avoiding $680/h grid penalties."
            },
            {
                "id": "INC-2026-088",
                "title": "Inverter #2 String #3 Fuse Blow & Voltage Collapse",
                "category": "ELECTRICAL_FAULT",
                "duration_sec": 100,
                "frames_count": 50,
                "peak_sec": 30,
                "description": "PV String STR-03 on central inverter INV-02 experiences open-circuit fuse failure (0V, 0A). Anomaly detector isolates string divergence against array median within 2 seconds."
            },
            {
                "id": "INC-2026-112",
                "title": "Critical Peak Tariff Surge ($0.58/kWh) & Arbitrage",
                "category": "MARKET_ARBITRAGE",
                "duration_sec": 100,
                "frames_count": 50,
                "peak_sec": 24,
                "description": "Day-ahead spot market price spike from $0.14 to $0.58/kWh. BESS optimizer dispatches 3,500 kW discretionary power, boosting revenue rate above $12,500/hr."
            }
        ]

    def generate_scenario_frames(self, scenario_id: str) -> List[Dict[str, Any]]:
        catalog = {s["id"]: s for s in self.get_catalog()}
        if scenario_id not in catalog:
            scenario_id = "INC-2026-041"

        meta = catalog[scenario_id]
        frames_count = meta["frames_count"]
        start_time = datetime(2026, 7, 15, 13, 30, 0)
        
        frames = []
        bess_soc = 68.0
        
        for f in range(frames_count):
            t_sec = f * 2
            curr_time = start_time + timedelta(seconds=t_sec)
            
            # Base parameters
            irradiance = 980.0
            wind_speed = 8.6
            ambient_temp = 32.0
            tariff_usd = 0.14
            committed_kw = 18500.0
            faulted_strings = {}
            inv_temp_overrides = {}

            # Apply scenario dynamics
            if scenario_id == "INC-2026-041":
                # Monsoonal cloud transit: drops between t=20s and t=80s
                if 20 <= t_sec <= 80:
                    depth = math.sin(math.pi * (t_sec - 20) / 60.0) # 0 to 1 back to 0
                    irradiance = 980.0 * (1.0 - 0.78 * depth)
            elif scenario_id == "INC-2026-088":
                # String 3 blown fuse from t=30s onwards
                if t_sec >= 30:
                    faulted_strings["INV-02:STR-03"] = "BLOWN_FUSE"
                    inv_temp_overrides["INV-02"] = 88.5 + (t_sec - 30) * 0.15
            elif scenario_id == "INC-2026-112":
                # Tariff spike between t=20s and t=80s
                if 20 <= t_sec <= 80:
                    tariff_usd = 0.58

            # Inverters and strings
            inverters = []
            total_solar_kw = 0.0
            for inv_id in settings.PLANT.inverters:
                strings = []
                inv_pwr = 0.0
                inv_temp = inv_temp_overrides.get(inv_id, 62.0 + (irradiance / 1000.0) * 18.0)

                for s_idx in range(1, 9):
                    str_id = f"STR-{s_idx:02d}"
                    v = 850.0
                    i = 18.5 * (irradiance / 1000.0)

                    key = f"{inv_id}:{str_id}"
                    if key in faulted_strings:
                        v = 0.0
                        i = 0.0

                    p_kw = (v * i) / 1000.0 * 20.0
                    inv_pwr += p_kw
                    strings.append({
                        "string_id": str_id,
                        "voltage_v": round(v, 2),
                        "current_a": round(i, 2),
                        "power_kw": round(p_kw, 2)
                    })

                ac_kw = min(5000.0, inv_pwr * 0.985)
                total_solar_kw += ac_kw
                inverters.append({
                    "inverter_id": inv_id,
                    "ac_power_kw": round(ac_kw, 2),
                    "dc_power_kw": round(inv_pwr, 2),
                    "inverter_temp_c": round(inv_temp, 1),
                    "status": "FAULT" if inv_temp >= 95.0 else ("WARNING" if (inv_temp >= 85.0 or any(s["voltage_v"] < 100 for s in strings)) else "NORMAL"),
                    "strings": strings
                })

            # Turbines
            turbines = []
            total_wind_kw = 0.0
            for wtg in settings.PLANT.turbines:
                p_wtg = 2500.0 * ((wind_speed**3 - 27.0) / (1728.0 - 27.0))
                p_wtg = max(0.0, min(2500.0, p_wtg))
                total_wind_kw += p_wtg
                turbines.append({
                    "turbine_id": wtg,
                    "power_kw": round(p_wtg, 2),
                    "wind_speed_ms": round(wind_speed, 2),
                    "rotor_rpm": 14.5,
                    "status": "NORMAL"
                })

            total_renewable_kw = total_solar_kw + total_wind_kw

            # Quantile forecast
            active_ratio = sum(1 for i in inverters if i["status"] != "FAULT") / 4.0
            forecast = self.forecaster.predict_15m_rolling(
                current_time=curr_time,
                irradiance_wm2=irradiance,
                ambient_temp_c=ambient_temp,
                wind_speed_ms=wind_speed,
                active_inverter_ratio=active_ratio
            )

            # BESS dispatch
            dispatch = self.dispatch_opt.optimize_dispatch(
                renewable_gen_kw=total_renewable_kw,
                forecast_15m_kw=forecast["predicted_total_kw"],
                committed_schedule_kw=committed_kw,
                current_soc_pct=bess_soc,
                tariff_usd_kwh=tariff_usd,
                p90_conservative_kw=forecast["p90_conservative_kw"],
                p10_optimistic_kw=forecast["p10_optimistic_kw"]
            )
            bess_soc = dispatch["updated_soc_pct"]

            # Alerts
            alerts = []
            for inv in inverters:
                alerts.extend(self.anomaly_detector.evaluate_inverter_strings(
                    plant_id=settings.PLANT.plant_id,
                    inverter_id=inv["inverter_id"],
                    strings_data=inv["strings"],
                    inverter_temp_c=inv["inverter_temp_c"],
                    timestamp=curr_time
                ))

            frames.append({
                "frame_index": f,
                "second_offset": t_sec,
                "timestamp": curr_time.isoformat(),
                "plant_id": settings.PLANT.plant_id,
                "scenario_id": scenario_id,
                "weather": {
                    "irradiance_wm2": round(irradiance, 2),
                    "wind_speed_ms": round(wind_speed, 2),
                    "ambient_temp_c": round(ambient_temp, 2),
                    "module_temp_c": round(ambient_temp + 0.03 * irradiance, 2)
                },
                "solar_generation_kw": round(total_solar_kw, 2),
                "wind_generation_kw": round(total_wind_kw, 2),
                "total_renewable_kw": round(total_renewable_kw, 2),
                "committed_schedule_kw": committed_kw,
                "tariff_usd_kwh": round(tariff_usd, 4),
                "inverters": inverters,
                "turbines": turbines,
                "forecast_15m": forecast,
                "bess_dispatch": dispatch,
                "bess_soc_pct": bess_soc,
                "active_alerts": alerts,
                "financial_kpis": {
                    "total_penalties_usd": 0.0,
                    "total_savings_usd": round(dispatch["penalty_avoided_usd_h"] * (t_sec / 3600.0), 2),
                    "total_revenue_usd": round(dispatch["revenue_rate_usd_h"] * (t_sec / 3600.0), 2),
                    "total_energy_mwh": round((total_renewable_kw * (t_sec / 3600.0)) / 1000.0, 3)
                }
            })

        return frames

scenario_archive = ScenarioArchive()
