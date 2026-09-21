import math
from datetime import datetime
from typing import Dict, Any

class SolarTrackerEngine:
    """
    Astronomical Solar Position & Single-Axis Horizontal Tracker Algorithm.
    Computes solar elevation, azimuth, zenith, and motorized tracker tilt angles
    with row-to-row backtracking to avoid early morning and late evening panel shading.
    
    Plant Coordinates (Solaria West, Mojave Desert):
    Latitude: 34.924 deg N
    Longitude: -116.892 deg W
    GCR (Ground Cover Ratio): 0.40 (ratio of panel collector width to row pitch)
    Max Mechanical Tilt: +/- 60.0 degrees
    """
    def __init__(self, latitude: float = 34.924, longitude: float = -116.892, gcr: float = 0.40, max_tilt_deg: float = 60.0):
        self.latitude = latitude
        self.longitude = longitude
        self.gcr = gcr  # Ground Cover Ratio: w / pitch
        self.max_tilt_deg = max_tilt_deg

    def calculate_solar_position(self, dt: datetime = None) -> Dict[str, float]:
        """
        Calculates the solar zenith, elevation, and azimuth angles using
        standard astronomical equations for the given datetime and plant location.
        """
        if dt is None:
            dt = datetime.now()

        # Day of year
        day_of_year = dt.timetuple().tm_yday
        hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

        # Fractional year in radians
        gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour_decimal - 12.0) / 24.0)

        # Equation of time (minutes)
        eq_time = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                            - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))

        # Solar declination angle (radians)
        decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
                - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
                - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))

        # Time offset in minutes (assuming local standard time UTC-8 for Pacific)
        # Time zone offset: longitude / 15.0 deg/hour
        time_offset = eq_time + 4.0 * (self.longitude - (-120.0))  # Relative to PST (UTC-8)
        true_solar_time = (hour_decimal * 60.0 + time_offset) % 1440.0

        # Solar hour angle (degrees to radians)
        hour_angle_deg = (true_solar_time / 4.0) - 180.0
        hour_angle_rad = math.radians(hour_angle_deg)

        lat_rad = math.radians(self.latitude)

        # Solar zenith angle (radians)
        cos_zenith = (math.sin(lat_rad) * math.sin(decl) +
                      math.cos(lat_rad) * math.cos(decl) * math.cos(hour_angle_rad))
        cos_zenith = max(-1.0, min(1.0, cos_zenith))
        zenith_rad = math.acos(cos_zenith)
        zenith_deg = math.degrees(zenith_rad)

        # Solar elevation angle (degrees)
        elevation_deg = 90.0 - zenith_deg

        # Solar azimuth angle (degrees from North clockwise)
        if elevation_deg > -89.0:
            cos_azimuth = ((math.sin(decl) - math.sin(lat_rad) * math.cos(zenith_rad)) /
                           (math.cos(lat_rad) * math.sin(zenith_rad) + 1e-7))
            cos_azimuth = max(-1.0, min(1.0, cos_azimuth))
            azimuth_rad = math.acos(cos_azimuth)
            azimuth_deg = math.degrees(azimuth_rad)
            if hour_angle_deg > 0:
                azimuth_deg = 360.0 - azimuth_deg
        else:
            azimuth_deg = 180.0

        return {
            "elevation_deg": round(elevation_deg, 2),
            "azimuth_deg": round(azimuth_deg, 2),
            "zenith_deg": round(zenith_deg, 2)
        }

    def calculate_tracker_tilt(self, elevation_deg: float, azimuth_deg: float) -> Dict[str, Any]:
        """
        Calculates single-axis horizontal tracker tilt with North-South torque tube axis.
        Rotation axis is along N-S (0 deg / 180 deg), panels rotate East-West.
        
        Backtracking:
        When solar elevation is low (near sunrise or sunset), true-tracking would cause
        panels to cast shadows on adjacent rows. Backtracking reduces the tilt angle:
        theta_backtrack = arcsin(sin(theta_ideal) / GCR) - theta_ideal (or similar geometric limit).
        """
        if elevation_deg <= 0.0:
            # Nighttime stow position (flat at 0 degrees or stowed to 0 to minimize wind load)
            return {
                "tracker_tilt_deg": 0.0,
                "mode": "NIGHT_STOW",
                "backtracking_active": False
            }

        zenith_rad = math.radians(90.0 - elevation_deg)
        azimuth_rad = math.radians(azimuth_deg)

        # Surface orientation: N-S axis, axis tilt = 0
        # True-tracking angle calculation for horizontal single axis tracker (N-S axis):
        # tan(theta_true) = tan(zenith) * sin(azimuth - 180) = sin(azimuth) * tan(zenith) relative to South
        # Panels tilt negative (East) in the morning, positive (West) in the afternoon.
        tan_tilt = math.tan(zenith_rad) * math.sin(azimuth_rad - math.pi)
        ideal_tilt_rad = math.atan(tan_tilt)
        ideal_tilt_deg = math.degrees(ideal_tilt_rad)

        # Backtracking calculation:
        # Avoid row-to-row shading when adjacent rows block direct beam irradiance.
        # Critical angle where shading begins: cos(theta) / sin(theta) = 1 / (GCR * sin(theta_true))
        backtracking_active = False
        tilt_deg = ideal_tilt_deg

        if abs(ideal_tilt_deg) > 0.1:
            # Limit based on GCR to avoid mutual shading
            # Maximum tilt without shading: sin(theta_backtrack) = sin(theta_true) * cos(theta_backtrack) ...
            # Approximation: if GCR * abs(sin(ideal_tilt_rad)) > cos(elevation_rad)
            cos_elevation = math.cos(math.radians(elevation_deg))
            if cos_elevation > 0 and self.gcr > 0:
                limit_ratio = cos_elevation / (self.gcr + 1e-6)
                if limit_ratio < 1.0:
                    max_allowed_tilt_rad = math.asin(limit_ratio)
                    max_allowed_tilt_deg = math.degrees(max_allowed_tilt_rad)
                    if abs(ideal_tilt_deg) > max_allowed_tilt_deg:
                        backtracking_active = True
                        sign = 1.0 if ideal_tilt_deg > 0 else -1.0
                        tilt_deg = sign * max_allowed_tilt_deg

        # Clamp to mechanical limits (+/- max_tilt_deg)
        tilt_deg = max(-self.max_tilt_deg, min(self.max_tilt_deg, tilt_deg))

        return {
            "tracker_tilt_deg": round(tilt_deg, 2),
            "mode": "BACKTRACKING" if backtracking_active else "TRUE_TRACKING",
            "backtracking_active": backtracking_active
        }

    def get_spatial_tracking(self, dt: datetime = None, wind_speed_ms: float = 8.5) -> Dict[str, Any]:
        """
        Generates full 3D spatial orientation telemetry packet for the digital twin.
        """
        sun = self.calculate_solar_position(dt)
        tracker = self.calculate_tracker_tilt(sun["elevation_deg"], sun["azimuth_deg"])

        # Wind turbine yaw angle (generally into the prevailing Mojave wind ~245 deg WSW)
        prevailing_wind_dir_deg = 245.0 + 10.0 * math.sin(dt.hour / 4.0 if dt else 0.0)

        return {
            "sun_elevation_deg": sun["elevation_deg"],
            "sun_azimuth_deg": sun["azimuth_deg"],
            "sun_zenith_deg": sun["zenith_deg"],
            "tracker_tilt_deg": tracker["tracker_tilt_deg"],
            "tracker_mode": tracker["mode"],
            "backtracking_active": tracker["backtracking_active"],
            "wind_yaw_deg": round(prevailing_wind_dir_deg % 360.0, 1),
            "gcr": self.gcr,
            "max_tilt_deg": self.max_tilt_deg
        }
