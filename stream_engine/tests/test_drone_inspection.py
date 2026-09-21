import unittest
from stream_engine.models.drone_inspection import DroneInspectionEngine

class TestDroneInspection(unittest.TestCase):
    def setUp(self):
        self.engine = DroneInspectionEngine()

    def test_initial_state(self):
        self.assertEqual(self.engine.state, "DOCKED")
        self.assertEqual(self.engine.pos_z, 0.0)
        self.assertEqual(self.engine.battery_pct, 98.0)

    def test_mission_lifecycle(self):
        # Start mission
        self.engine.start_mission()
        self.assertEqual(self.engine.state, "TAKEOFF")
        
        # Advance takeoff
        for _ in range(15):
            self.engine.update(dt_seconds=1.0)
        self.assertEqual(self.engine.state, "INSPECTING")
        self.assertEqual(self.engine.pos_z, 35.0)

    def test_thermal_defect_detection(self):
        self.engine.start_mission()
        self.engine.pos_z = 35.0
        self.engine.state = "INSPECTING"
        # Place drone near INV-02 waypoint
        self.engine.current_waypoint_idx = 0
        
        # Inject string fault on INV-02:STR-03
        disturbances = {
            "string_faults": {
                "INV-02:STR-03": "PARTIAL_SHADING"
            }
        }
        res = self.engine.update(active_disturbances=disturbances, ambient_temp_c=25.0, dt_seconds=2.0)
        
        # Verify FLIR camera caught the hot spot
        self.assertGreater(len(res["flir_camera"]["defects_in_view"]), 0)
        defect = res["flir_camera"]["defects_in_view"][0]
        self.assertEqual(defect["type"], "HOT_SPOT_CELL")
        self.assertEqual(defect["severity"], "CLASS_3")
        self.assertGreater(defect["spot_temp_c"], 60.0)

    def test_generate_report(self):
        report = self.engine.generate_inspection_report()
        self.assertIn("report_id", report)
        self.assertIn("standard", report)
        self.assertIn("IEC 62446-3", report["standard"])

if __name__ == "__main__":
    unittest.main()
