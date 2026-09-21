import unittest
from stream_engine.models.frequency_droop import FrequencyDroopEngine

class TestFrequencyDroop(unittest.TestCase):
    def setUp(self):
        self.engine = FrequencyDroopEngine(f0=60.00, rated_power_kw=5000.0, droop_s=0.04, h_constant_s=4.5)

    def test_nominal_deadband(self):
        # In deadband [59.97, 60.03], droop power should be 0.0
        self.engine.current_freq_hz = 60.010
        self.engine.previous_freq_hz = 60.010
        res = self.engine.update(dt_seconds=2.0)
        self.assertEqual(res["p_droop_kw"], 0.0)
        self.assertFalse(res["ffr_active"])
        self.assertEqual(res["frequency_status"], "DEADBAND_NORMAL")

    def test_under_frequency_generator_trip(self):
        # Simulate generator trip
        self.engine.trigger_generator_trip(loss_mw=1200.0)
        res = self.engine.update(dt_seconds=2.0)
        # Should be below 59.80 Hz and trigger FFR burst
        self.assertLessEqual(res["grid_frequency_hz"], 59.80)
        self.assertTrue(res["ffr_active"])
        self.assertEqual(res["p_ffr_burst_kw"], 5000.0)
        self.assertGreater(res["total_fcr_kw"], 4000.0)
        self.assertEqual(res["frequency_status"], "CRITICAL_FFR_BURST")

    def test_over_frequency_load_shed(self):
        # Simulate load shedding / rejection
        self.engine.trigger_load_shed(load_mw=800.0)
        res = self.engine.update(dt_seconds=2.0)
        # Should be above 60.05 Hz and droop should absorb power (negative kW)
        self.assertGreater(res["grid_frequency_hz"], 60.05)
        self.assertLess(res["p_droop_kw"], -500.0)
        self.assertLess(res["total_fcr_kw"], 0.0)
        self.assertIn(res["frequency_status"], ["OVER_FREQUENCY_CURTAILMENT", "DEADBAND_NORMAL"])

    def test_ancillary_revenue_accumulation(self):
        initial_revenue = self.engine.accumulated_ancillary_usd
        self.engine.update(dt_seconds=10.0)
        self.assertGreater(self.engine.accumulated_ancillary_usd, initial_revenue)

if __name__ == "__main__":
    unittest.main()
