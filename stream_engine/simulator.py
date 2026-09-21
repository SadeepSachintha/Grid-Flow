import time
import math
import random
from datetime import datetime
from typing import Dict, List, Any
from stream_engine.config import settings
from stream_engine.models.solar_tracker import SolarTrackerEngine
from stream_engine.models.cloud_motion import CloudMotionEngine
from stream_engine.models.frequency_droop import FrequencyDroopEngine
from stream_engine.models.battery_health import BatteryHealthEngine

class TelemetrySimulator:
    """
    Industrial IoT Telemetry Generator.
    Produces high-fidelity 2-second telemetry packets for solar strings,
    inverters, wind turbines, weather stations, and BESS storage.
    Supports on-the-fly disturbance injections (passing clouds, wind lulls, string fuse trips).
    """
    def __init__(self):
        self.plant_cfg = settings.PLANT
        self.sim_time_offset_sec = 0.0
        self.tracker_engine = SolarTrackerEngine(
            latitude=self.plant_cfg.latitude,
            longitude=self.plant_cfg.longitude
        )
        self.cloud_engine = CloudMotionEngine(
            cloud_base_height_m=1200.0,
            plant_radius_m=250.0
        )
        self.frequency_engine = FrequencyDroopEngine(
            f0=60.00,
            rated_power_kw=self.plant_cfg.bess_max_power_mw * 1000.0,
            droop_s=0.04,
            h_constant_s=4.5
        )
        self.bess_health_engine = BatteryHealthEngine(
            capacity_mwh=self.plant_cfg.bess_capacity_mwh,
            nominal_voltage_v=850.0
        )
        
        # State & Active Disturbances
        self.active_disturbances: Dict[str, Any] = {
            "cloud_cover": {"active": False, "remaining_sec": 0, "drop_pct": 0.0},
            "wind_lull": {"active": False, "remaining_sec": 0, "drop_pct": 0.0},
            "wind_gust": {"active": False, "remaining_sec": 0, "boost_pct": 0.0},
            "string_faults": {}, # e.g. {"INV-02:STR-03": "BLOWN_FUSE"}
            "inverter_overheat": {}, # e.g. {"INV-01": 96.5}
            "tariff_spike": {"active": False, "remaining_sec": 0, "tariff_usd": 0.0}
        }
        
        # Battery state
        self.battery_soc_pct = self.plant_cfg.bess_initial_soc_pct
        self.accumulated_penalty_usd = 0.0
        self.accumulated_savings_usd = 0.0

    def trigger_cloud_cover(self, duration_sec: int = 40, drop_pct: float = 75.0):
        self.active_disturbances["cloud_cover"] = {
            "active": True, "remaining_sec": duration_sec, "drop_pct": drop_pct
        }
        self.cloud_engine.trigger_approaching_cloud(speed_ms=16.0, heading_deg=65.0, distance_m=1200.0)

    def trigger_wind_lull(self, duration_sec: int = 30, drop_pct: float = 70.0):
        self.active_disturbances["wind_lull"] = {
            "active": True, "remaining_sec": duration_sec, "drop_pct": drop_pct
        }

    def trigger_wind_gust(self, duration_sec: int = 30, boost_pct: float = 60.0):
        self.active_disturbances["wind_gust"] = {
            "active": True, "remaining_sec": duration_sec, "boost_pct": boost_pct
        }

    def trigger_string_fault(self, inverter_id: str = "INV-02", string_id: str = "STR-03", fault_type: str = "BLOWN_FUSE"):
        key = f"{inverter_id}:{string_id}"
        self.active_disturbances["string_faults"][key] = fault_type

    def clear_string_fault(self, inverter_id: str = "INV-02", string_id: str = "STR-03"):
        key = f"{inverter_id}:{string_id}"
        if key in self.active_disturbances["string_faults"]:
            del self.active_disturbances["string_faults"][key]

    def trigger_inverter_overheat(self, inverter_id: str = "INV-01", temp_c: float = 96.5):
        self.active_disturbances["inverter_overheat"][inverter_id] = temp_c

    def trigger_tariff_spike(self, tariff_usd: float = 0.58, duration_sec: int = 60):
        self.active_disturbances["tariff_spike"] = {
            "active": True, "remaining_sec": duration_sec, "tariff_usd": tariff_usd
        }

    def reset_disturbances(self):
        self.active_disturbances = {
            "cloud_cover": {"active": False, "remaining_sec": 0, "drop_pct": 0.0},
            "wind_lull": {"active": False, "remaining_sec": 0, "drop_pct": 0.0},
            "wind_gust": {"active": False, "remaining_sec": 0, "boost_pct": 0.0},
            "string_faults": {},
            "inverter_overheat": {},
            "tariff_spike": {"active": False, "remaining_sec": 0, "tariff_usd": 0.0}
        }

    def _get_current_tariff(self, current_hour: float) -> float:
        if self.active_disturbances["tariff_spike"]["active"]:
            return self.active_disturbances["tariff_spike"]["tariff_usd"]
            
        if 14.0 <= current_hour < 19.0:
            return 0.32  # Peak Tariff ($/kWh)
        elif (7.0 <= current_hour < 14.0) or (19.0 <= current_hour < 22.0):
            return 0.14  # Shoulder Tariff ($/kWh)
        else:
            return 0.06  # Off-Peak Tariff ($/kWh)

    def _get_committed_schedule(self, current_hour: float) -> float:
        """
        Calculates contractual committed generation schedule (kW).
        Typically follows a firm dispatch curve committed day-ahead to the grid operator.
        """
        if 6.0 <= current_hour <= 18.5:
            # Solar peak commitment: up to 18,000 kW + 3,000 kW wind
            solar_commitment = 17500.0 * math.sin(math.pi * (current_hour - 6.0) / 12.5)
            wind_commitment = 2800.0
            return round(max(0.0, solar_commitment + wind_commitment), 2)
        else:
            # Nighttime wind commitment
            return 2800.0

    def generate_packet(self, dt: datetime = None) -> Dict[str, Any]:
        """
        Generates a complete 2-second telemetry packet for the entire plant.
        """
        if dt is None:
            dt = datetime.now()
            
        current_hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        
        # 1. Base Weather
        base_irradiance = 0.0
        if 6.0 <= current_hour <= 18.5:
            base_irradiance = 980.0 * math.sin(math.pi * (current_hour - 6.0) / 12.5)
            # Add minor atmospheric turbulence
            base_irradiance += random.gauss(0, 15.0)
            base_irradiance = max(0.0, min(1100.0, base_irradiance))
            
        base_wind_speed = 8.5 + 2.5 * math.sin(current_hour / 3.0) + random.gauss(0, 0.4)
        base_ambient_temp = 22.0 + 8.0 * math.sin(math.pi * (current_hour - 8.0) / 12.0) + random.gauss(0, 0.2)
        
        # Apply disturbances & decrement counters
        irradiance = base_irradiance
        if self.active_disturbances["cloud_cover"]["active"]:
            drop = self.active_disturbances["cloud_cover"]["drop_pct"] / 100.0
            irradiance *= (1.0 - drop)
            self.active_disturbances["cloud_cover"]["remaining_sec"] -= 2
            if self.active_disturbances["cloud_cover"]["remaining_sec"] <= 0:
                self.active_disturbances["cloud_cover"]["active"] = False

        wind_speed = base_wind_speed
        if self.active_disturbances["wind_lull"]["active"]:
            drop = self.active_disturbances["wind_lull"]["drop_pct"] / 100.0
            wind_speed *= (1.0 - drop)
            self.active_disturbances["wind_lull"]["remaining_sec"] -= 2
            if self.active_disturbances["wind_lull"]["remaining_sec"] <= 0:
                self.active_disturbances["wind_lull"]["active"] = False
        elif self.active_disturbances["wind_gust"]["active"]:
            boost = self.active_disturbances["wind_gust"]["boost_pct"] / 100.0
            wind_speed *= (1.0 + boost)
            self.active_disturbances["wind_gust"]["remaining_sec"] -= 2
            if self.active_disturbances["wind_gust"]["remaining_sec"] <= 0:
                self.active_disturbances["wind_gust"]["active"] = False

        if self.active_disturbances["tariff_spike"]["active"]:
            self.active_disturbances["tariff_spike"]["remaining_sec"] -= 2
            if self.active_disturbances["tariff_spike"]["remaining_sec"] <= 0:
                self.active_disturbances["tariff_spike"]["active"] = False

        module_temp = base_ambient_temp + ((self.plant_cfg.nominal_string_voltage_v / 1000.0) * 0.03 * irradiance)
        
        # 2. Inverters & Strings
        inverters_data = []
        total_solar_kw = 0.0
        
        for inv_id in self.plant_cfg.inverters:
            strings = []
            inv_power_kw = 0.0
            inv_temp = 55.0 + (irradiance / 1000.0) * 22.0 + random.gauss(0, 0.5)
            
            # Check for overheat disturbance
            if inv_id in self.active_disturbances["inverter_overheat"]:
                inv_temp = self.active_disturbances["inverter_overheat"][inv_id]

            for str_num in range(1, self.plant_cfg.strings_per_inverter + 1):
                str_id = f"STR-{str_num:02d}"
                fault_key = f"{inv_id}:{str_id}"
                
                v = self.plant_cfg.nominal_string_voltage_v + random.gauss(0, 3.5)
                irr_ratio = max(0.0, irradiance / 1000.0)
                i = self.plant_cfg.nominal_string_current_a * irr_ratio + random.gauss(0, 0.15)
                
                # Check for string fault
                if fault_key in self.active_disturbances["string_faults"]:
                    f_type = self.active_disturbances["string_faults"][fault_key]
                    if f_type == "BLOWN_FUSE":
                        v = 0.0
                        i = 0.0
                    elif f_type == "PARTIAL_SHADING":
                        v *= 0.65
                        i *= 0.70
                    elif f_type == "BYPASS_DIODE_SHORT":
                        v *= 0.67
                
                p_kw = (v * i) / 1000.0 * 20.0  # Scale for 20 panels per string
                inv_power_kw += p_kw
                
                strings.append({
                    "string_id": str_id,
                    "voltage_v": round(v, 2),
                    "current_a": round(i, 2),
                    "power_kw": round(p_kw, 2)
                })
                
            # Inverter AC conversion with clipping at rated 5000 kW
            ac_power_kw = min(5000.0, inv_power_kw * 0.985)
            total_solar_kw += ac_power_kw
            
            inverters_data.append({
                "inverter_id": inv_id,
                "ac_power_kw": round(ac_power_kw, 2),
                "dc_power_kw": round(inv_power_kw, 2),
                "inverter_temp_c": round(inv_temp, 1),
                "status": "FAULT" if inv_temp >= 95.0 else ("WARNING" if inv_temp >= 85.0 else "NORMAL"),
                "strings": strings
            })
            
        # 3. Wind Turbines
        turbines_data = []
        total_wind_kw = 0.0
        for wtg_id in self.plant_cfg.turbines:
            # Cut-in: 3 m/s, Rated: 12 m/s, Cut-out: 25 m/s
            if wind_speed < 3.0 or wind_speed >= 25.0:
                p_wtg_kw = 0.0
                rpm = 0.0
            elif wind_speed >= 12.0:
                p_wtg_kw = 2500.0 + random.gauss(0, 10.0)
                rpm = 16.0 + random.gauss(0, 0.2)
            else:
                ratio = (wind_speed**3 - 3.0**3) / (12.0**3 - 3.0**3)
                p_wtg_kw = 2500.0 * ratio + random.gauss(0, 15.0)
                rpm = 6.0 + 10.0 * (wind_speed - 3.0) / 9.0
                
            p_wtg_kw = max(0.0, min(2500.0, p_wtg_kw))
            total_wind_kw += p_wtg_kw
            turbines_data.append({
                "turbine_id": wtg_id,
                "power_kw": round(p_wtg_kw, 2),
                "wind_speed_ms": round(wind_speed, 2),
                "rotor_rpm": round(rpm, 1),
                "status": "NORMAL"
            })

        committed_schedule_kw = self._get_committed_schedule(current_hour)
        current_tariff = self._get_current_tariff(current_hour)
        spatial_tracking = self.tracker_engine.get_spatial_tracking(dt, wind_speed_ms=wind_speed)
        cloud_tracking = self.cloud_engine.update(
            dt=dt,
            sun_elevation_deg=spatial_tracking["sun_elevation_deg"],
            sun_azimuth_deg=spatial_tracking["sun_azimuth_deg"],
            wind_speed_ms=wind_speed,
            wind_yaw_deg=spatial_tracking["wind_yaw_deg"],
            dt_seconds=2.0
        )
        
        frequency_response = self.frequency_engine.update(dt_seconds=2.0)
        bess_health = self.bess_health_engine.update(
            bess_dispatch_kw=frequency_response.get("total_fcr_kw", 0.0),
            soc_pct=self.battery_soc_pct,
            dt_seconds=2.0
        )
        
        return {
            "timestamp": dt.isoformat(),
            "plant_id": self.plant_cfg.plant_id,
            "weather": {
                "irradiance_wm2": round(irradiance, 2),
                "wind_speed_ms": round(wind_speed, 2),
                "ambient_temp_c": round(base_ambient_temp, 2),
                "module_temp_c": round(module_temp, 2)
            },
            "solar_generation_kw": round(total_solar_kw, 2),
            "wind_generation_kw": round(total_wind_kw, 2),
            "total_renewable_kw": round(total_solar_kw + total_wind_kw, 2),
            "committed_schedule_kw": committed_schedule_kw,
            "tariff_usd_kwh": round(current_tariff, 4),
            "spatial_tracking": spatial_tracking,
            "cloud_tracking": cloud_tracking,
            "frequency_response": frequency_response,
            "bess_health": bess_health,
            "inverters": inverters_data,
            "turbines": turbines_data,
            "disturbances": {k: v for k, v in self.active_disturbances.items() if v}
        }
