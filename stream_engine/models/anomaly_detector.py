import numpy as np
from datetime import datetime
from typing import List, Dict, Any

class InverterAnomalyDetector:
    """
    Real-time Inverter & PV String Anomaly Detector.
    Evaluates 2-second string telemetry to identify blown fuses, partial shading,
    thermal throttling, and grid compliance risks.
    """
    def __init__(self, voltage_mismatch_threshold_pct: float = 12.0, temp_warn_c: float = 85.0, temp_crit_c: float = 95.0):
        self.voltage_mismatch_threshold_pct = voltage_mismatch_threshold_pct
        self.temp_warn_c = temp_warn_c
        self.temp_crit_c = temp_crit_c

    def evaluate_inverter_strings(
        self,
        plant_id: str,
        inverter_id: str,
        strings_data: List[Dict[str, Any]],
        inverter_temp_c: float,
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Analyzes string voltages and currents for a specific inverter.
        Returns a list of detected alerts/anomalies.
        """
        alerts = []
        if not strings_data:
            return alerts
            
        voltages = [s["voltage_v"] for s in strings_data if s.get("voltage_v") is not None]
        currents = [s["current_a"] for s in strings_data if s.get("current_a") is not None]
        
        if not voltages:
            return alerts
            
        median_voltage = float(np.median(voltages))
        
        # 1. Check String Voltage / Current Mismatch
        for s in strings_data:
            s_id = s.get("string_id", "STR-??")
            v = s.get("voltage_v", 0.0)
            i = s.get("current_a", 0.0)
            
            # Fuse blown or disconnected string
            if v < 50.0 and median_voltage > 400.0:
                alerts.append({
                    "plant_id": plant_id,
                    "inverter_id": inverter_id,
                    "string_id": s_id,
                    "alert_type": "STRING_OPEN_CIRCUIT_OR_FUSE_BLOWN",
                    "severity": "CRITICAL",
                    "message": f"String {s_id} voltage dropped to {v:.1f}V (inverter median: {median_voltage:.1f}V). Probable blown fuse or disconnect.",
                    "metric_value": v,
                    "threshold_value": median_voltage * 0.2,
                    "detected_at": timestamp.isoformat()
                })
            elif median_voltage > 100.0:
                dev_pct = abs(v - median_voltage) / median_voltage * 100.0
                if dev_pct > self.voltage_mismatch_threshold_pct:
                    severity = "CRITICAL" if dev_pct > 25.0 else "WARNING"
                    alerts.append({
                        "plant_id": plant_id,
                        "inverter_id": inverter_id,
                        "string_id": s_id,
                        "alert_type": "STRING_VOLTAGE_MISMATCH",
                        "severity": severity,
                        "message": f"String {s_id} deviates by {dev_pct:.1f}% from array median ({v:.1f}V vs {median_voltage:.1f}V). Possible partial shading, bypass diode conduction, or soiling.",
                        "metric_value": round(v, 1),
                        "threshold_value": round(median_voltage, 1),
                        "detected_at": timestamp.isoformat()
                    })
                    
        # 2. Inverter Thermal Anomaly
        if inverter_temp_c >= self.temp_crit_c:
            alerts.append({
                "plant_id": plant_id,
                "inverter_id": inverter_id,
                "string_id": None,
                "alert_type": "INVERTER_OVERHEAT_CRITICAL",
                "severity": "CRITICAL",
                "message": f"Inverter IGBT heatsink temperature is {inverter_temp_c:.1f}°C, exceeding critical limit ({self.temp_crit_c}°C). Imminent thermal trip!",
                "metric_value": round(inverter_temp_c, 1),
                "threshold_value": self.temp_crit_c,
                "detected_at": timestamp.isoformat()
            })
        elif inverter_temp_c >= self.temp_warn_c:
            alerts.append({
                "plant_id": plant_id,
                "inverter_id": inverter_id,
                "string_id": None,
                "alert_type": "INVERTER_TEMPERATURE_HIGH",
                "severity": "WARNING",
                "message": f"Inverter IGBT temperature elevated at {inverter_temp_c:.1f}°C (warning threshold: {self.temp_warn_c}°C). Cooling check advised.",
                "metric_value": round(inverter_temp_c, 1),
                "threshold_value": self.temp_warn_c,
                "detected_at": timestamp.isoformat()
            })
            
        return alerts

    def evaluate_grid_compliance(
        self,
        plant_id: str,
        actual_injected_kw: float,
        committed_schedule_kw: float,
        tolerance_pct: float,
        bess_available_dispatch_kw: float,
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Evaluates real-time power injection compliance with contractual grid dispatch schedules.
        """
        alerts = []
        if committed_schedule_kw <= 0:
            return alerts
            
        deviation_kw = actual_injected_kw - committed_schedule_kw
        deviation_pct = abs(deviation_kw) / committed_schedule_kw * 100.0
        
        if deviation_pct > tolerance_pct:
            # Check if BESS has enough reserve to cover the deficit/excess
            uncovered_kw = abs(deviation_kw) - bess_available_dispatch_kw
            if uncovered_kw > 0:
                severity = "CRITICAL" if deviation_pct > (tolerance_pct * 2) else "WARNING"
                direction = "under-generating (shortfall)" if deviation_kw < 0 else "over-injecting"
                alerts.append({
                    "plant_id": plant_id,
                    "inverter_id": "SUBSTATION-01",
                    "string_id": None,
                    "alert_type": "GRID_DISPATCH_DEVIATION_PENALTY_RISK",
                    "severity": severity,
                    "message": f"Plant injection is {direction} by {abs(deviation_kw):.1f} kW ({deviation_pct:.1f}% deviation, tolerance: ±{tolerance_pct}%). BESS cannot fully compensate. Grid penalty accruing.",
                    "metric_value": round(actual_injected_kw, 1),
                    "threshold_value": round(committed_schedule_kw, 1),
                    "detected_at": timestamp.isoformat()
                })
                
        return alerts
