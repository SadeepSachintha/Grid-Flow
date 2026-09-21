import unittest
from stream_engine.models.vpp_trading import VppTradingEngine
from stream_engine.simulator import TelemetrySimulator

class TestVppTrading(unittest.TestCase):
    def setUp(self):
        self.engine = VppTradingEngine()

    def test_merit_order_clearing(self):
        # Update with 18 MW solar/wind generation and 0 BESS dispatch
        res = self.engine.update(
            total_renewable_kw=18000.0,
            bess_dispatch_kw=0.0,
            bess_soc_pct=65.0,
            dt_seconds=2.0
        )
        self.assertIn("market_clearing_price_usd_mwh", res)
        self.assertIn("cleared_volume_mw", res)
        self.assertGreater(res["cleared_volume_mw"], 0.0)
        self.assertGreater(res["market_clearing_price_usd_mwh"], 10.0)
        self.assertGreaterEqual(res["consumer_surplus_usd"], 0.0)
        self.assertGreaterEqual(res["producer_surplus_usd"], 0.0)
        self.assertEqual(len(res["assets"]), 4)

    def test_nodal_lmp_calculation(self):
        res = self.engine.update(
            total_renewable_kw=15000.0,
            bess_dispatch_kw=0.0,
            bess_soc_pct=50.0,
            dt_seconds=2.0
        )
        mcp = res["market_clearing_price_usd_mwh"]
        assets_dict = {a["id"]: a for a in res["assets"]}
        
        # Boron Lithium has transmission congestion on Feeder 3, so its LMP must exceed base MCP
        boron_lmp = assets_dict["BORON_LITHIUM"]["lmp_usd_mwh"]
        self.assertGreater(boron_lmp, mcp)

    def test_rec_token_cryptography(self):
        token = self.engine._generate_rec_token(
            trade_id="TX-TEST-001",
            seller_id="SOLARIA_WEST",
            buyer_id="MOJAVE_H2",
            mwh=10.0,
            timestamp="2026-09-21T12:00:00Z"
        )
        self.assertTrue(token["hash_proof"].startswith("0x"))
        self.assertEqual(len(token["hash_proof"]), 66) # "0x" + 64 hex characters
        # 10 MWh * 0.385 tCO2/MWh = 3.85 tCO2
        self.assertAlmostEqual(token["co2_avoided_tons"], 3.85, places=2)

    def test_market_event_triggers(self):
        # 1. Electrolyzer Surge
        self.engine.trigger_electrolyzer_surge(extra_mw=3.2, max_bid=52.0)
        res = self.engine.update(18000.0, 0.0, 65.0)
        h2_asset = next(a for a in res["assets"] if a["id"] == "MOJAVE_H2")
        self.assertGreaterEqual(h2_asset["current_power_mw"], 7.5)
        self.assertEqual(h2_asset["marginal_bid_mwh"], 52.0)

        # 2. Data Center Curtailment
        self.engine.trigger_datacenter_curtailment(shed_mw=1.5)
        res = self.engine.update(18000.0, 0.0, 65.0)
        compute_asset = next(a for a in res["assets"] if a["id"] == "MOJAVE_COMPUTE")
        self.assertTrue(compute_asset["curtailed"])
        self.assertLessEqual(compute_asset["current_power_mw"], 2.6)

        # 3. Reset
        self.engine.reset_market()
        res = self.engine.update(18000.0, 0.0, 65.0)
        compute_reset = next(a for a in res["assets"] if a["id"] == "MOJAVE_COMPUTE")
        self.assertFalse(compute_reset["curtailed"])

    def test_simulator_integration(self):
        sim = TelemetrySimulator()
        packet = sim.generate_packet()
        self.assertIn("vpp_trading", packet)
        vpp = packet["vpp_trading"]
        self.assertIn("market_clearing_price_usd_mwh", vpp)
        self.assertIn("assets", vpp)
        self.assertIn("order_book", vpp)
        self.assertIn("recent_transactions", vpp)

if __name__ == "__main__":
    unittest.main()
