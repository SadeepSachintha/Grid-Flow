import math
import random
from datetime import datetime
from typing import Dict, List, Any, Tuple

class CloudMotionEngine:
    """
    All-Sky Cloud Motion Vector (CMV) & Optical Flow Tracking Engine.
    Simulates a ground-based All-Sky Imager (180-deg fisheye lens) capturing
    sky frames every few seconds.
    
    Performs:
    1. Cloud detection via Red-Blue Difference / intensity thresholding.
    2. Optical flow vector computation (u, v) estimating cloud speed & heading.
    3. Ground shadow trajectory projection using solar zenith & azimuth angles.
    4. Time-to-Impact (TTI) countdown and solar ramp-rate (MW/min) prediction.
    5. Automatic BESS Fast-Ramp Buffer priming to prevent grid ramp-down violations.
    """
    def __init__(self, cloud_base_height_m: float = 1200.0, plant_radius_m: float = 250.0):
        self.cloud_base_height_m = cloud_base_height_m  # Typical Mojave cumulus base: 1,200m
        self.plant_radius_m = plant_radius_m            # Microgrid boundary radius: 250m
        
        # State: 2D cloud field (relative coordinates in meters at cloud height)
        # Position (x, y) relative to zenith (0, 0), where x = East, y = North
        self.clouds: List[Dict[str, float]] = [
            {"x": -1800.0, "y": -900.0, "radius_m": 600.0, "optical_depth": 0.85, "active": True},
            {"x": 1200.0, "y": 1500.0, "radius_m": 450.0, "optical_depth": 0.65, "active": True}
        ]
        
        self.last_update_time = None
        self.grid_ramp_limit_mw_min = -2.0  # CAISO / ERCOT -2.0 MW/min ramp penalty limit

    def trigger_approaching_cloud(self, speed_ms: float = 16.0, heading_deg: float = 65.0, distance_m: float = 1400.0):
        """
        Manually injects an approaching cumulus cloud cluster headed directly
        toward the plant along the prevailing wind vector.
        """
        # Calculate start position based on heading and distance
        heading_rad = math.radians(heading_deg)
        # Cloud moves in direction of heading, so it starts opposite:
        start_x = -distance_m * math.sin(heading_rad)
        start_y = -distance_m * math.cos(heading_rad)
        
        self.clouds = [
            {
                "x": start_x,
                "y": start_y,
                "radius_m": 700.0,
                "optical_depth": 0.90,
                "active": True
            },
            {
                "x": start_x - 400.0,
                "y": start_y - 300.0,
                "radius_m": 500.0,
                "optical_depth": 0.75,
                "active": True
            }
        ]

    def update(
        self, 
        dt: datetime = None, 
        sun_elevation_deg: float = 48.0, 
        sun_azimuth_deg: float = 194.0, 
        wind_speed_ms: float = 8.5,
        wind_yaw_deg: float = 245.0,
        dt_seconds: float = 2.0
    ) -> Dict[str, Any]:
        """
        Updates cloud positions, computes optical flow vectors, calculates
        ground shadow projection, and predicts solar ramp-rate.
        """
        if dt is None:
            dt = datetime.now()

        # Cloud velocity at 1,200m altitude is typically 1.6x - 2.0x surface wind speed
        cloud_speed_ms = max(5.0, wind_speed_ms * 1.8)
        # Cloud heading follows prevailing wind direction (meteorological degrees to cartesian)
        cloud_heading_deg = wind_yaw_deg % 360.0
        cloud_heading_rad = math.radians(cloud_heading_deg)
        
        # Velocity components (x = East, y = North)
        vx = cloud_speed_ms * math.sin(cloud_heading_rad)
        vy = cloud_speed_ms * math.cos(cloud_heading_rad)

        # Advect cloud field
        for cloud in self.clouds:
            cloud["x"] += vx * dt_seconds
            cloud["y"] += vy * dt_seconds

            # Wrap around if cloud moved way past the horizon (> 4000m)
            if math.hypot(cloud["x"], cloud["y"]) > 4500.0:
                cloud["x"] = -3000.0 * math.sin(cloud_heading_rad) + random.gauss(0, 300)
                cloud["y"] = -3000.0 * math.cos(cloud_heading_rad) + random.gauss(0, 300)

        # 1. Ground Shadow Projection
        # Using cloud base height (CBH) and solar zenith / azimuth:
        zenith_deg = max(5.0, 90.0 - sun_elevation_deg)
        zenith_rad = math.radians(zenith_deg)
        azimuth_rad = math.radians(sun_azimuth_deg)

        # Shadow offset vector on ground:
        # Sunlight comes FROM (azimuth), so shadow is cast TOWARD (azimuth + 180):
        shadow_dist = self.cloud_base_height_m * math.tan(zenith_rad)
        shadow_dx = -shadow_dist * math.sin(azimuth_rad)
        shadow_dy = -shadow_dist * math.cos(azimuth_rad)

        # 2. Analyze closest cloud shadow to plant center (0, 0)
        min_shadow_distance = 99999.0
        active_cloud_shadow = None
        closest_cloud = None

        for cloud in self.clouds:
            # Ground shadow coordinates
            gx = cloud["x"] + shadow_dx
            gy = cloud["y"] + shadow_dy
            dist_to_center = math.hypot(gx, gy)

            if dist_to_center < min_shadow_distance:
                min_shadow_distance = dist_to_center
                closest_cloud = cloud
                active_cloud_shadow = {"gx": gx, "gy": gy, "radius_m": cloud["radius_m"]}

        # 3. Time-to-Impact (TTI) Calculation
        # Distance from current shadow front to plant perimeter (plant_radius_m)
        dist_to_perimeter = max(0.0, min_shadow_distance - self.plant_radius_m)
        
        # Relative velocity towards plant center
        dot_product = -(active_cloud_shadow["gx"] * vx + active_cloud_shadow["gy"] * vy)
        radial_speed = dot_product / (min_shadow_distance + 1e-6)

        if radial_speed > 0.5:
            time_to_impact_sec = round(dist_to_perimeter / radial_speed, 1)
        else:
            time_to_impact_sec = 999.0  # Moving away or stationary

        # 4. Shadow Coverage & Ramp-Rate Prediction
        # If shadow is currently over plant:
        shadow_coverage_pct = 0.0
        if min_shadow_distance < (self.plant_radius_m + active_cloud_shadow["radius_m"]):
            # Overlap fraction
            overlap = 1.0 - (min_shadow_distance / (self.plant_radius_m + active_cloud_shadow["radius_m"]))
            shadow_coverage_pct = round(min(100.0, max(0.0, overlap * 100.0)), 1)

        # Predicted power ramp rate (MW/min)
        # 20 MW solar capacity. Full shadow drops ~75% generation (15 MW) over ~2.5 minutes (~6.0 MW/min drop)
        predicted_ramp_mw_min = 0.0
        if time_to_impact_sec < 180.0:
            expected_drop_mw = 15.0 * (closest_cloud["optical_depth"])
            transit_time_min = max(0.8, (2.0 * self.plant_radius_m) / (cloud_speed_ms * 60.0))
            predicted_ramp_mw_min = round(-expected_drop_mw / transit_time_min, 2)
        elif shadow_coverage_pct > 10.0:
            predicted_ramp_mw_min = round(-15.0 * (shadow_coverage_pct / 100.0) / 1.5, 2)

        # Ramp Violation Risk
        ramp_violation_risk = "NORMAL"
        if predicted_ramp_mw_min <= -3.5:
            ramp_violation_risk = "CRITICAL_RAMP_DOWN"
        elif predicted_ramp_mw_min <= self.grid_ramp_limit_mw_min:
            ramp_violation_risk = "WARNING_RAMP_DOWN"

        # BESS Fast-Ramp Buffer Priming
        # Prime BESS if a critical ramp-down is predicted within 120 seconds
        bess_fast_ramp_primed = (time_to_impact_sec <= 120.0 and predicted_ramp_mw_min < self.grid_ramp_limit_mw_min)

        # 5. Fisheye Sky Polar Coordinates for SCADA Radar Display
        # Project clouds into fisheye polar coordinates:
        # Distance from zenith r_fisheye in [0, 1], theta in [0, 360)
        sky_clouds_display = []
        for cloud in self.clouds:
            dist_horiz = math.hypot(cloud["x"], cloud["y"])
            zenith_angle_rad = math.atan2(dist_horiz, self.cloud_base_height_m)
            r_normalized = min(1.0, zenith_angle_rad / (math.pi / 2.0))
            
            polar_angle_deg = (math.degrees(math.atan2(cloud["x"], cloud["y"])) + 360.0) % 360.0
            
            sky_clouds_display.append({
                "r": round(r_normalized, 3),
                "angle_deg": round(polar_angle_deg, 1),
                "radius_norm": round(cloud["radius_m"] / self.cloud_base_height_m * 0.4, 3),
                "optical_depth": cloud["optical_depth"],
                "vx_norm": round(vx / 50.0, 3),
                "vy_norm": round(vy / 50.0, 3)
            })

        return {
            "cloud_cover_pct": round(min(100.0, len(self.clouds) * 22.5), 1),
            "cloud_speed_ms": round(cloud_speed_ms, 1),
            "cloud_heading_deg": round(cloud_heading_deg, 1),
            "cloud_base_height_m": self.cloud_base_height_m,
            "time_to_impact_sec": time_to_impact_sec,
            "predicted_ramp_mw_min": predicted_ramp_mw_min,
            "grid_ramp_limit_mw_min": self.grid_ramp_limit_mw_min,
            "ramp_violation_risk": ramp_violation_risk,
            "bess_fast_ramp_primed": bess_fast_ramp_primed,
            "shadow_coverage_pct": shadow_coverage_pct,
            "ground_shadow": {
                "x_m": round(active_cloud_shadow["gx"], 1),
                "y_m": round(active_cloud_shadow["gy"], 1),
                "radius_m": round(active_cloud_shadow["radius_m"], 1),
                "dist_to_center_m": round(min_shadow_distance, 1)
            },
            "sky_clouds": sky_clouds_display
        }
