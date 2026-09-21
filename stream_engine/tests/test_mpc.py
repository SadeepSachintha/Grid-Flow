import unittest
from datetime import datetime
from stream_engine.models.mpc_optimizer import mpc_controller

class TestMpcController(unittest.TestCase):
    def test_mpc_4h_optimization(self):
        dt = datetime(2026, 7, 15, 12, 0, 0)
        res = mpc_controller.optimize_4h_horizon(
            start_time=dt,
            current_soc_pct=65.0,
            current_forecast_p50_kw=17500.0
        )
        self.assertEqual(res["status"], "OPTIMAL")
        self.assertEqual(len(res["intervals"]), 16)
        
        # Verify physical constraints
        for interval in res["intervals"]:
            # SoC constraint: 10% <= SoC <= 90%
            self.assertGreaterEqual(interval["predicted_soc_pct"], 9.9)
            self.assertLessEqual(interval["predicted_soc_pct"], 90.1)

            # BESS power limits: -5000 kW <= P_bess <= 5000 kW
            self.assertGreaterEqual(interval["optimal_bess_kw"], -5000.1)
            self.assertLessEqual(interval["optimal_bess_kw"], 5000.1)

            # Injected power >= 0
            self.assertGreaterEqual(interval["optimal_injected_kw"], 0.0)

        summary = res["summary"]
        self.assertGreater(summary["projected_revenue_usd"], 0.0)
        self.assertGreaterEqual(summary["projected_degradation_usd"], 0.0)
        print(f"[TEST] MPC 4-Hour Plan: Status={res['status']}, Net Profit=${summary['net_profit_usd']}, Degradation Cost=${summary['projected_degradation_usd']}")

if __name__ == "__main__":
    unittest.main()
