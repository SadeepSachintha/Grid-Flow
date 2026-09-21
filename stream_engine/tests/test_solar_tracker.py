import unittest
from datetime import datetime
from stream_engine.models.solar_tracker import SolarTrackerEngine

class TestSolarTracker(unittest.TestCase):
    def setUp(self):
        self.engine = SolarTrackerEngine(latitude=34.924, longitude=-116.892, gcr=0.40, max_tilt_deg=60.0)

    def test_solar_position_noon(self):
        # Summer solstice solar noon approx 13:00 PDT (12:00 PST)
        dt = datetime(2026, 6, 21, 12, 0, 0)
        pos = self.engine.calculate_solar_position(dt)
        self.assertIn("elevation_deg", pos)
        self.assertIn("azimuth_deg", pos)
        self.assertIn("zenith_deg", pos)
        # At Mojave desert summer noon, elevation should be high (> 70 deg)
        self.assertGreater(pos["elevation_deg"], 65.0)
        self.assertLess(pos["zenith_deg"], 25.0)

    def test_solar_position_night(self):
        dt = datetime(2026, 6, 21, 1, 0, 0)
        pos = self.engine.calculate_solar_position(dt)
        self.assertLess(pos["elevation_deg"], 0.0)
        tracker = self.engine.calculate_tracker_tilt(pos["elevation_deg"], pos["azimuth_deg"])
        self.assertEqual(tracker["mode"], "NIGHT_STOW")
        self.assertEqual(tracker["tracker_tilt_deg"], 0.0)

    def test_tracker_tilt_limits(self):
        # Morning sun
        dt = datetime(2026, 6, 21, 7, 30, 0)
        spatial = self.engine.get_spatial_tracking(dt, wind_speed_ms=9.0)
        self.assertIn("tracker_tilt_deg", spatial)
        self.assertIn("wind_yaw_deg", spatial)
        # Tilt must obey +/- 60 deg mechanical limit
        self.assertGreaterEqual(spatial["tracker_tilt_deg"], -60.0)
        self.assertLessEqual(spatial["tracker_tilt_deg"], 60.0)

    def test_backtracking_low_elevation(self):
        # Low sun elevation (e.g. 5 deg above horizon)
        tracker = self.engine.calculate_tracker_tilt(elevation_deg=5.0, azimuth_deg=95.0)
        self.assertIn(tracker["mode"], ["BACKTRACKING", "TRUE_TRACKING"])
        self.assertLessEqual(abs(tracker["tracker_tilt_deg"]), 60.0)

if __name__ == "__main__":
    unittest.main()
