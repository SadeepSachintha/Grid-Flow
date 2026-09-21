import unittest
from stream_engine.models.battery_health import BatteryHealthEngine

class TestBatteryHealth(unittest.TestCase):
    def setUp(self):
        self.engine = BatteryHealthEngine(capacity_mwh=10.0, nominal_voltage_v=850.0)

    def test_ecm_voltage_calculation(self):
        # Test 2RC Thevenin ECM terminal voltage
        ecm = self.engine.calculate_ecm_voltage(soc_pct=65.0, current_a=100.0)
        self.assertIn("v_ocv", ecm)
        self.assertIn("v_terminal", ecm)
        self.assertIn("v_r0_drop", ecm)
        # Terminal voltage must be less than OCV during discharge (positive current)
        self.assertLess(ecm["v_terminal"], ecm["v_ocv"])
        self.assertGreater(ecm["v_r0_drop"], 0.0)

    def test_soh_metrics(self):
        res = self.engine.update(bess_dispatch_kw=1000.0, soc_pct=65.0, dt_seconds=2.0)
        self.assertGreaterEqual(res["soh_capacity_pct"], 90.0)
        self.assertGreaterEqual(res["soh_resistance_pct"], 90.0)
        self.assertIn("r0_ohmic_mohm", res)
        self.assertIn("ecm_voltage", res)
        self.assertEqual(len(res["racks"]), 16)

    def test_thermal_runaway_drill_and_interlock(self):
        # Trigger drill on BESS-01:RACK-03
        self.engine.trigger_thermal_runaway_drill("BESS-01:RACK-03")
        
        # Advance simulation by 30 seconds into Stage 3 (Off-gas detection)
        for _ in range(15):
            res = self.engine.update(bess_dispatch_kw=0.0, soc_pct=65.0, dt_seconds=2.0)

        # Off-gas alarm should be active
        self.assertTrue(res["off_gas_sensors"]["alarm_active"])
        self.assertGreater(res["off_gas_sensors"]["h2_ppm"], 20.0)
        # Contactor should be tripped to isolate faulty rack
        self.assertTrue(res["emergency_contactor_tripped"])
        target_rack = next(r for r in res["racks"] if r["rack_id"] == "BESS-01:RACK-03")
        self.assertEqual(target_rack["contactor_status"], "TRIPPED_ISOLATED")

    def test_reset_bess_health(self):
        self.engine.trigger_thermal_runaway_drill("BESS-01:RACK-03")
        self.engine.update(dt_seconds=30.0)
        self.engine.reset_bess_health()
        res = self.engine.update(dt_seconds=2.0)
        self.assertFalse(res["drill_active"])
        self.assertFalse(res["emergency_contactor_tripped"])
        self.assertEqual(res["thermal_runaway_status"], "STAGE_0_NORMAL")

if __name__ == "__main__":
    unittest.main()
