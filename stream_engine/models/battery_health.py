import math
import random
from datetime import datetime
from typing import Dict, List, Any

class BatteryHealthEngine:
    """
    BESS Battery Health (SOH), 2RC Thevenin ECM & Thermal Runaway Early Warning System.
    Models 10.0 MWh / 5.0 MW LiFePO4 battery storage system (4 Megapack containers,
    each with 4 Racks containing 16 cell modules).
    
    Equivalent Circuit Model (2RC Thevenin):
    - R0: Ohmic internal resistance (~0.85 mOhm, grows with SEI degradation)
    - R1, C1: Charge-transfer resistance & double-layer capacitance (~1.2 mOhm, 2500 F)
    - R2, C2: Diffusion / concentration polarization (~2.1 mOhm, 8000 F)
    
    Thermal Runaway Early Warning (NFPA 855 / UL 9540A):
    - Stage 1: Cell voltage micro-short (delta V > 25 mV below rack median)
    - Stage 2: Cell differential thermal surge (delta T > 5.0 deg C)
    - Stage 3: Off-gas detection (H2 > 20 ppm, CO > 15 ppm)
    - Stage 4: Exothermic thermal runaway (T > 75 deg C, dT/dt > 1.0 deg C/s)
    - Automated DC contactor emergency trip (< 50ms)
    """
    def __init__(self, capacity_mwh: float = 10.0, nominal_voltage_v: float = 850.0):
        self.capacity_mwh = capacity_mwh
        self.nominal_voltage_v = nominal_voltage_v
        
        # Fresh cell ECM parameters
        self.r0_fresh_mohm = 0.85
        self.r1_mohm = 1.20
        self.c1_f = 2500.0
        self.r2_mohm = 2.10
        self.c2_f = 8000.0
        
        # State of Health
        self.total_throughput_mwh = 1420.0
        self.cycle_count = 142
        self.soh_capacity_pct = 98.4
        self.r0_current_mohm = 0.885
        self.soh_resistance_pct = round((self.r0_fresh_mohm / self.r0_current_mohm) * 100.0, 1)

        # Off-Gas Sensors (ppm)
        self.gas_h2_ppm = 1.2
        self.gas_co_ppm = 0.8
        self.gas_voc_ppm = 4.5
        
        # Thermal & Electrical State for 4 Containers x 4 Racks (16 racks total)
        self.racks: Dict[str, Dict[str, Any]] = {}
        for c in range(1, 5):
            c_id = f"BESS-0{c}"
            for r in range(1, 5):
                r_id = f"{c_id}:RACK-0{r}"
                self.racks[r_id] = {
                    "container_id": c_id,
                    "rack_id": r_id,
                    "contactor_status": "CLOSED_NORMAL",  # "CLOSED_NORMAL" | "TRIPPED_ISOLATED"
                    "avg_temp_c": 24.2 + random.gauss(0, 0.4),
                    "max_cell_temp_c": 25.1,
                    "min_cell_voltage_v": 3.285,
                    "max_cell_voltage_v": 3.292,
                    "voltage_spread_mv": 7.0,
                    "stage": "STAGE_0_NORMAL"
                }

        # Drill / Active Anomaly
        self.drill_active = False
        self.drill_target_rack = "BESS-01:RACK-03"
        self.drill_time_sec = 0.0

    def trigger_thermal_runaway_drill(self, target_rack: str = "BESS-01:RACK-03"):
        """
        Simulates an internal dendrite micro-short and cell venting in a specific rack.
        Advances through Stage 1 (voltage dip) -> Stage 2 (thermal surge) -> 
        Stage 3 (H2 off-gassing) -> automated contactor trip.
        """
        self.drill_active = True
        self.drill_target_rack = target_rack
        self.drill_time_sec = 0.0

    def reset_bess_health(self):
        """Restores nominal battery health and clears drills."""
        self.drill_active = False
        self.drill_time_sec = 0.0
        self.gas_h2_ppm = 1.2
        self.gas_co_ppm = 0.8
        self.gas_voc_ppm = 4.5
        
        for r_id, rack in self.racks.items():
            rack["contactor_status"] = "CLOSED_NORMAL"
            rack["avg_temp_c"] = 24.2 + random.gauss(0, 0.4)
            rack["max_cell_temp_c"] = 25.1
            rack["min_cell_voltage_v"] = 3.285
            rack["max_cell_voltage_v"] = 3.292
            rack["voltage_spread_mv"] = 7.0
            rack["stage"] = "STAGE_0_NORMAL"

    def calculate_ecm_voltage(self, soc_pct: float, current_a: float) -> Dict[str, float]:
        """
        Computes 2RC Thevenin ECM cell terminal voltage:
        V_term = V_ocv(SoC) - I * R0 - V1 - V2
        """
        # LiFePO4 OCV curve approximation (3.0V at 0%, 3.29V plateau from 20-80%, 3.45V at 100%)
        if soc_pct < 10.0:
            v_ocv = 3.00 + (soc_pct / 10.0) * 0.22
        elif soc_pct > 90.0:
            v_ocv = 3.32 + ((soc_pct - 90.0) / 10.0) * 0.13
        else:
            v_ocv = 3.22 + ((soc_pct - 10.0) / 80.0) * 0.10

        # R0 ohmic drop
        r0_ohm = self.r0_current_mohm / 1000.0
        v_r0 = current_a * r0_ohm

        # Steady-state overpotentials V1 = I * R1, V2 = I * R2
        v1 = current_a * (self.r1_mohm / 1000.0)
        v2 = current_a * (self.r2_mohm / 1000.0)

        v_terminal = v_ocv - v_r0 - v1 - v2

        return {
            "v_ocv": round(v_ocv, 3),
            "v_terminal": round(v_terminal, 3),
            "v_r0_drop": round(v_r0, 4),
            "v_polarization": round(v1 + v2, 4)
        }

    def update(self, bess_dispatch_kw: float = 0.0, soc_pct: float = 65.0, dt_seconds: float = 2.0) -> Dict[str, Any]:
        """
        Advances battery health state, processes off-gas telemetry, and evaluates
        thermal runaway safety interlocks.
        """
        # Current per cell module (assuming ~1,200 strings in parallel/series)
        current_a = (bess_dispatch_kw * 1000.0) / (self.nominal_voltage_v + 1e-6) / 4.0
        ecm = self.calculate_ecm_voltage(soc_pct, current_a)

        # Update drill progress if active
        if self.drill_active:
            self.drill_time_sec += dt_seconds
            target = self.racks[self.drill_target_rack]

            if self.drill_time_sec < 10.0:
                # Stage 1: Micro-Short (Cell voltage dip)
                target["min_cell_voltage_v"] = max(2.95, target["min_cell_voltage_v"] - 0.03 * dt_seconds)
                target["voltage_spread_mv"] = round((target["max_cell_voltage_v"] - target["min_cell_voltage_v"]) * 1000.0, 1)
                target["stage"] = "STAGE_1_MICRO_SHORT"

            elif self.drill_time_sec < 25.0:
                # Stage 2: Differential Thermal Surge
                target["max_cell_temp_c"] += 1.8 * dt_seconds
                target["stage"] = "STAGE_2_THERMAL_SURGE"
                self.gas_h2_ppm = min(15.0, self.gas_h2_ppm + 1.2 * dt_seconds)

            elif self.drill_time_sec < 45.0:
                # Stage 3: Off-Gassing Detected!
                target["max_cell_temp_c"] += 2.5 * dt_seconds
                self.gas_h2_ppm = min(120.0, self.gas_h2_ppm + 6.5 * dt_seconds)
                self.gas_co_ppm = min(85.0, self.gas_co_ppm + 4.2 * dt_seconds)
                target["stage"] = "STAGE_3_OFF_GAS_WARNING"

                # Automated Emergency Isolation Interlock Trigger:
                # If H2 > 20 ppm or Max Temp > 60 C, trip the DC contactor to isolate the rack!
                if self.gas_h2_ppm > 20.0 or target["max_cell_temp_c"] > 55.0:
                    target["contactor_status"] = "TRIPPED_ISOLATED"
            else:
                # Cooling down after contactor isolation
                target["max_cell_temp_c"] = max(35.0, target["max_cell_temp_c"] - 0.8 * dt_seconds)
                self.gas_h2_ppm = max(5.0, self.gas_h2_ppm - 2.0 * dt_seconds)
        else:
            # Ambient baseline drift
            self.gas_h2_ppm = max(0.5, min(2.5, 1.2 + random.gauss(0, 0.1)))
            self.gas_co_ppm = max(0.3, min(1.8, 0.8 + random.gauss(0, 0.05)))

        # Find worst-case rack
        max_rack_temp = max(r["max_cell_temp_c"] for r in self.racks.values())
        any_tripped = any(r["contactor_status"] == "TRIPPED_ISOLATED" for r in self.racks.values())
        overall_stage = "STAGE_0_NORMAL"
        for r in self.racks.values():
            if r["stage"] != "STAGE_0_NORMAL":
                overall_stage = r["stage"]
                break

        return {
            "soh_capacity_pct": self.soh_capacity_pct,
            "soh_resistance_pct": self.soh_resistance_pct,
            "r0_ohmic_mohm": self.r0_current_mohm,
            "total_throughput_mwh": round(self.total_throughput_mwh + (abs(bess_dispatch_kw) * dt_seconds / 3600.0 / 1000.0), 2),
            "cycle_count": self.cycle_count,
            "ecm_voltage": ecm,
            "off_gas_sensors": {
                "h2_ppm": round(self.gas_h2_ppm, 1),
                "co_ppm": round(self.gas_co_ppm, 1),
                "voc_ppm": round(self.gas_voc_ppm, 1),
                "h2_threshold_ppm": 20.0,
                "alarm_active": self.gas_h2_ppm > 20.0 or self.gas_co_ppm > 15.0
            },
            "thermal_runaway_status": overall_stage,
            "max_cell_temp_c": round(max_rack_temp, 1),
            "emergency_contactor_tripped": any_tripped,
            "drill_active": self.drill_active,
            "drill_target_rack": self.drill_target_rack if self.drill_active else None,
            "racks": list(self.racks.values())
        }
