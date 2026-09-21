import math
import random
from datetime import datetime
from typing import Dict, List, Any

class DroneInspectionEngine:
    """
    Autonomous Drone Thermography & Aerial IR Inspection Engine (IEC 62446-3).
    Simulates an autonomous enterprise drone (e.g. DJI Matrice 350 RTK with Zenmuse H20T
    radiometric thermal FLIR camera) flying waypoint grid missions across Solaria West.
    
    Features:
    - 16 Waypoint flight plan covering Inverters INV-01 to INV-04 (32 strings).
    - Flight physics: 35m AGL, 4.5 m/s ground speed, 80% front overlap.
    - Radiometric FLIR spot temperature & defect detection (IEC 62446-3 taxonomy):
        - HOT_SPOT_CELL (delta T > 15 C)
        - BYPASS_DIODE_FAILURE (delta T > 10 C)
        - STRING_OPEN_CIRCUIT (string cooler than operating panels)
        - PID_EFFECT (potential induced degradation)
    - Correlates thermal hot spots with active string disturbances in simulator.
    """
    def __init__(self):
        # Drone Base Coordinates (Home Dock Station at Substation x=100, y=0)
        self.home_x = 100.0
        self.home_y = 0.0
        self.cruise_altitude_m = 35.0
        self.cruise_speed_ms = 4.5
        
        # Flight State
        self.state = "DOCKED"  # "DOCKED" | "TAKEOFF" | "INSPECTING" | "RTH" | "LANDED"
        self.pos_x = self.home_x
        self.pos_y = self.home_y
        self.pos_z = 0.0
        self.heading_deg = 270.0
        self.battery_pct = 98.0
        self.current_waypoint_idx = 0
        self.mission_progress_pct = 0.0
        
        # 16 Inspection Waypoints (covering the 4 Inverter zones)
        # INV-01: (-60, -40), INV-02: (40, -40), INV-03: (-60, 40), INV-04: (40, 40)
        self.waypoints = [
            {"id": "WP-01", "x": 50.0, "y": -50.0, "zone": "INV-02", "target_strings": ["STR-01", "STR-02"]},
            {"id": "WP-02", "x": 30.0, "y": -50.0, "zone": "INV-02", "target_strings": ["STR-03", "STR-04"]},
            {"id": "WP-03", "x": 30.0, "y": -30.0, "zone": "INV-02", "target_strings": ["STR-05", "STR-06"]},
            {"id": "WP-04", "x": 50.0, "y": -30.0, "zone": "INV-02", "target_strings": ["STR-07", "STR-08"]},

            {"id": "WP-05", "x": -50.0, "y": -50.0, "zone": "INV-01", "target_strings": ["STR-01", "STR-02"]},
            {"id": "WP-06", "x": -70.0, "y": -50.0, "zone": "INV-01", "target_strings": ["STR-03", "STR-04"]},
            {"id": "WP-07", "x": -70.0, "y": -30.0, "zone": "INV-01", "target_strings": ["STR-05", "STR-06"]},
            {"id": "WP-08", "x": -50.0, "y": -30.0, "zone": "INV-01", "target_strings": ["STR-07", "STR-08"]},

            {"id": "WP-09", "x": -50.0, "y": 30.0, "zone": "INV-03", "target_strings": ["STR-01", "STR-02"]},
            {"id": "WP-10", "x": -70.0, "y": 30.0, "zone": "INV-03", "target_strings": ["STR-03", "STR-04"]},
            {"id": "WP-11", "x": -70.0, "y": 50.0, "zone": "INV-03", "target_strings": ["STR-05", "STR-06"]},
            {"id": "WP-12", "x": -50.0, "y": 50.0, "zone": "INV-03", "target_strings": ["STR-07", "STR-08"]},

            {"id": "WP-13", "x": 30.0, "y": 30.0, "zone": "INV-04", "target_strings": ["STR-01", "STR-02"]},
            {"id": "WP-14", "x": 50.0, "y": 30.0, "zone": "INV-04", "target_strings": ["STR-03", "STR-04"]},
            {"id": "WP-15", "x": 50.0, "y": 50.0, "zone": "INV-04", "target_strings": ["STR-05", "STR-06"]},
            {"id": "WP-16", "x": 30.0, "y": 50.0, "zone": "INV-04", "target_strings": ["STR-07", "STR-08"]}
        ]
        
        # Catalog of cataloged defects
        self.detected_defects: List[Dict[str, Any]] = []

    def start_mission(self):
        """Launches autonomous drone mission from home dock."""
        self.state = "TAKEOFF"
        self.current_waypoint_idx = 0
        self.battery_pct = 98.0
        self.detected_defects = []
        self.mission_progress_pct = 0.0

    def abort_mission(self):
        """Commands immediate Return-to-Home (RTH)."""
        self.state = "RTH"

    def update(self, active_disturbances: Dict[str, Any] = None, ambient_temp_c: float = 24.0, dt_seconds: float = 2.0) -> Dict[str, Any]:
        """
        Advances drone flight dynamics along waypoints and computes radiometric
        FLIR camera detections.
        """
        if active_disturbances is None:
            active_disturbances = {}

        # 1. Flight State Machine
        if self.state == "TAKEOFF":
            self.pos_z += 3.0 * dt_seconds
            self.battery_pct -= 0.05 * dt_seconds
            if self.pos_z >= self.cruise_altitude_m:
                self.pos_z = self.cruise_altitude_m
                self.state = "INSPECTING"

        elif self.state == "INSPECTING":
            target_wp = self.waypoints[self.current_waypoint_idx]
            dx = target_wp["x"] - self.pos_x
            dy = target_wp["y"] - self.pos_y
            dist = math.hypot(dx, dy)

            # Update heading
            if dist > 0.5:
                self.heading_deg = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0

            # Move towards waypoint
            step = self.cruise_speed_ms * dt_seconds
            if dist <= step:
                self.pos_x = target_wp["x"]
                self.pos_y = target_wp["y"]
                self.current_waypoint_idx += 1
                self.mission_progress_pct = round((self.current_waypoint_idx / len(self.waypoints)) * 100.0, 1)

                if self.current_waypoint_idx >= len(self.waypoints):
                    self.state = "RTH"
            else:
                self.pos_x += (dx / dist) * step
                self.pos_y += (dy / dist) * step

            self.battery_pct = max(10.0, self.battery_pct - 0.04 * dt_seconds)

        elif self.state == "RTH":
            dx = self.home_x - self.pos_x
            dy = self.home_y - self.pos_y
            dist = math.hypot(dx, dy)

            if dist > 1.0:
                self.heading_deg = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
                step = (self.cruise_speed_ms * 1.5) * dt_seconds
                self.pos_x += (dx / dist) * min(step, dist)
                self.pos_y += (dy / dist) * min(step, dist)
            else:
                # Land
                self.pos_z = max(0.0, self.pos_z - 2.5 * dt_seconds)
                if self.pos_z <= 0.0:
                    self.pos_z = 0.0
                    self.state = "DOCKED"
                    self.mission_progress_pct = 100.0

            self.battery_pct = max(5.0, self.battery_pct - 0.04 * dt_seconds)

        # 2. Radiometric FLIR Thermal Camera Simulation
        # Baseline panel temperature is ambient + 25C when operational (~49C)
        normal_panel_temp = ambient_temp_c + 25.0 + random.gauss(0, 0.5)
        spot_temp_c = normal_panel_temp
        current_defects_in_frame = []

        if self.state in ["INSPECTING", "RTH"] and self.pos_z > 10.0:
            current_wp = self.waypoints[min(self.current_waypoint_idx, len(self.waypoints) - 1)]
            zone_id = current_wp["zone"]
            
            # Check if there is an active fault in this inverter zone
            string_faults = active_disturbances.get("string_faults", {})
            for fault_key, fault_type in string_faults.items():
                if fault_key.startswith(zone_id):
                    # Drone is flying over the faulty string!
                    if fault_type == "BLOWN_FUSE":
                        # Open circuit string: cooler than active panels (~31C)
                        spot_temp_c = ambient_temp_c + 7.0
                        defect = {
                            "type": "STRING_OPEN_CIRCUIT",
                            "severity": "CLASS_2",
                            "delta_t_c": -18.0,
                            "spot_temp_c": round(spot_temp_c, 1),
                            "target": fault_key,
                            "bbox": [140, 110, 220, 190],
                            "recommendation": "Inspect DC fuseholder and string disconnect switch."
                        }
                    elif fault_type == "PARTIAL_SHADING":
                        # Shaded cell hotspot: cell heats up to 68C
                        spot_temp_c = normal_panel_temp + 22.5
                        defect = {
                            "type": "HOT_SPOT_CELL",
                            "severity": "CLASS_3",
                            "delta_t_c": 22.5,
                            "spot_temp_c": round(spot_temp_c, 1),
                            "target": fault_key,
                            "bbox": [180, 130, 240, 175],
                            "recommendation": "Severe hot spot. Thermal bypass diode activation or cracked wafer. Replace panel."
                        }
                    else:
                        spot_temp_c = normal_panel_temp + 14.0
                        defect = {
                            "type": "BYPASS_DIODE_FAILURE",
                            "severity": "CLASS_2",
                            "delta_t_c": 14.0,
                            "spot_temp_c": round(spot_temp_c, 1),
                            "target": fault_key,
                            "bbox": [160, 120, 260, 160],
                            "recommendation": "Sub-string overheating. Bypass diode shorted."
                        }

                    current_defects_in_frame.append(defect)
                    # Add to catalog if not already present
                    if not any(d["target"] == fault_key for d in self.detected_defects):
                        self.detected_defects.append(defect)

            # Inverter overheat disturbance
            inverter_overheats = active_disturbances.get("inverter_overheat", {})
            if zone_id in inverter_overheats:
                spot_temp_c = inverter_overheats[zone_id]
                inv_defect = {
                    "type": "INVERTER_IGBT_SURGE",
                    "severity": "CLASS_3",
                    "delta_t_c": spot_temp_c - 55.0,
                    "spot_temp_c": spot_temp_c,
                    "target": zone_id,
                    "bbox": [120, 80, 280, 220],
                    "recommendation": "Inverter heatsink exceeds thermal limit. Fan failure or cabinet air filter clogged."
                }
                current_defects_in_frame.append(inv_defect)
                if not any(d["target"] == zone_id for d in self.detected_defects):
                    self.detected_defects.append(inv_defect)

        return {
            "state": self.state,
            "position": {
                "x_m": round(self.pos_x, 1),
                "y_m": round(self.pos_y, 1),
                "z_alt_m": round(self.pos_z, 1)
            },
            "heading_deg": round(self.heading_deg, 1),
            "battery_pct": round(self.battery_pct, 1),
            "speed_ms": self.cruise_speed_ms if self.state in ["INSPECTING", "RTH"] else 0.0,
            "current_waypoint": self.waypoints[min(self.current_waypoint_idx, len(self.waypoints) - 1)]["id"],
            "mission_progress_pct": self.mission_progress_pct,
            "flir_camera": {
                "spot_temp_c": round(spot_temp_c, 1),
                "ambient_temp_c": round(ambient_temp_c, 1),
                "emissivity": 0.88,
                "palette": "IRONBOW",
                "defects_in_view": current_defects_in_frame
            },
            "cataloged_defects": self.detected_defects,
            "total_defects_count": len(self.detected_defects),
            "waypoints": self.waypoints
        }

    def generate_inspection_report(self) -> Dict[str, Any]:
        """
        Generates full IEC 62446-3 Aerial Photovoltaic Thermography Report.
        """
        return {
            "report_id": f"AERIAL-IR-{datetime.now().strftime('%Y%m%d-%H%M')}",
            "standard": "IEC 62446-3 (Outdoor Photovoltaic Thermography)",
            "plant_id": "PLANT-SOLARIA-01",
            "timestamp": datetime.now().isoformat(),
            "flight_altitude_m": self.cruise_altitude_m,
            "total_defects_found": len(self.detected_defects),
            "defects": self.detected_defects,
            "status": "CRITICAL_ACTION_REQUIRED" if any(d["severity"] == "CLASS_3" for d in self.detected_defects) else "NORMAL"
        }
