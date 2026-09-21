import unittest
from datetime import datetime
from stream_engine.models.cloud_motion import CloudMotionEngine

class TestCloudMotion(unittest.TestCase):
    def setUp(self):
        self.engine = CloudMotionEngine(cloud_base_height_m=1200.0, plant_radius_m=250.0)

    def test_cloud_motion_update(self):
        # Update with midday sun and 10 m/s wind
        result = self.engine.update(
            dt=datetime(2026, 6, 21, 12, 0, 0),
            sun_elevation_deg=75.0,
            sun_azimuth_deg=180.0,
            wind_speed_ms=10.0,
            wind_yaw_deg=240.0,
            dt_seconds=2.0
        )
        self.assertIn("cloud_speed_ms", result)
        self.assertIn("time_to_impact_sec", result)
        self.assertIn("predicted_ramp_mw_min", result)
        self.assertIn("bess_fast_ramp_primed", result)
        self.assertIn("ground_shadow", result)
        self.assertIn("sky_clouds", result)
        self.assertGreaterEqual(result["cloud_speed_ms"], 10.0)

    def test_approaching_cloud_trigger(self):
        # Trigger an approaching cloud 1000m away headed towards plant
        self.engine.trigger_approaching_cloud(speed_ms=20.0, heading_deg=90.0, distance_m=1000.0)
        
        # Sun overhead (zenith=0, shadow directly below cloud)
        result = self.engine.update(
            sun_elevation_deg=89.0,
            sun_azimuth_deg=180.0,
            wind_speed_ms=12.0,
            wind_yaw_deg=90.0,
            dt_seconds=2.0
        )
        # Should have finite positive TTI < 150s
        self.assertLess(result["time_to_impact_sec"], 150.0)
        self.assertGreater(result["time_to_impact_sec"], 0.0)
        # BESS should be primed
        self.assertTrue(result["bess_fast_ramp_primed"])
        self.assertIn(result["ramp_violation_risk"], ["WARNING_RAMP_DOWN", "CRITICAL_RAMP_DOWN"])

    def test_shadow_projection_geometry(self):
        # Low sun angle (elevation = 30 deg -> zenith = 60 deg -> tan(60) = 1.732)
        # At 1200m CBH, shadow offset is approx 1200 * 1.732 = 2078m
        result = self.engine.update(
            sun_elevation_deg=30.0,
            sun_azimuth_deg=180.0,
            wind_speed_ms=8.0,
            wind_yaw_deg=245.0,
            dt_seconds=2.0
        )
        self.assertIsNotNone(result["ground_shadow"])
        self.assertIn("dist_to_center_m", result["ground_shadow"])

if __name__ == "__main__":
    unittest.main()
