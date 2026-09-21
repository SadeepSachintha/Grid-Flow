import unittest
from stream_engine.scenario_archive import scenario_archive

class TestScenarioArchive(unittest.TestCase):
    def test_catalog_retrieval(self):
        catalog = scenario_archive.get_catalog()
        self.assertGreaterEqual(len(catalog), 3)
        ids = [c["id"] for c in catalog]
        self.assertIn("INC-2026-041", ids)
        self.assertIn("INC-2026-088", ids)
        self.assertIn("INC-2026-112", ids)
        print(f"[TEST] Scenario Catalog Retrieved: {len(catalog)} recorded incidents.")

    def test_scenario_frames_generation(self):
        frames = scenario_archive.generate_scenario_frames("INC-2026-041")
        self.assertEqual(len(frames), 60)
        
        # Check cloud depth at peak (t=50s -> frame 25)
        mid_frame = frames[25]
        self.assertLess(mid_frame["weather"]["irradiance_wm2"], 500.0)
        self.assertGreater(mid_frame["bess_dispatch"]["battery_dispatch_kw"], 2000.0)
        print(f"[TEST] INC-2026-041 Frame 25: Irradiance dropped to {mid_frame['weather']['irradiance_wm2']} W/m2, BESS dispatched {mid_frame['bess_dispatch']['battery_dispatch_kw']} kW.")

    def test_string_fault_scenario(self):
        frames = scenario_archive.generate_scenario_frames("INC-2026-088")
        # Check frame at t=40s (frame 20)
        fault_frame = frames[20]
        inv2 = next(i for i in fault_frame["inverters"] if i["inverter_id"] == "INV-02")
        str3 = next(s for s in inv2["strings"] if s["string_id"] == "STR-03")
        self.assertEqual(str3["voltage_v"], 0.0)
        self.assertTrue(any(a["string_id"] == "STR-03" for a in fault_frame["active_alerts"]))
        print(f"[TEST] INC-2026-088 Frame 20: String STR-03 voltage is 0.0V, Alert correctly generated: {fault_frame['active_alerts'][0]['message']}")

if __name__ == "__main__":
    unittest.main()
