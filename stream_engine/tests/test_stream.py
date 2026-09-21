import unittest
from datetime import datetime
from stream_engine.models.yield_forecaster import RenewableYieldForecaster
from stream_engine.models.anomaly_detector import InverterAnomalyDetector
from stream_engine.models.dispatch_optimizer import BatteryDispatchOptimizer
from stream_engine.simulator import TelemetrySimulator
from stream_engine.stream_worker import StreamWorker

class TestGridFlowStreamEngine(unittest.TestCase):
    def setUp(self):
        self.forecaster = RenewableYieldForecaster(solar_capacity_kw=20000.0, wind_capacity_kw=5000.0)
        self.anomaly_detector = InverterAnomalyDetector()
        self.dispatch_opt = BatteryDispatchOptimizer(capacity_kwh=10000.0, max_power_kw=5000.0)
        self.simulator = TelemetrySimulator()
        self.worker = StreamWorker()

    def test_yield_forecaster_inference(self):
        dt = datetime(2026, 6, 21, 12, 0, 0)
        forecast = self.forecaster.predict_15m_rolling(
            current_time=dt,
            irradiance_wm2=950.0,
            ambient_temp_c=28.0,
            wind_speed_ms=9.5,
            active_inverter_ratio=1.0
        )
        self.assertIn("predicted_total_kw", forecast)
        self.assertGreater(forecast["predicted_total_kw"], 5000.0)
        self.assertLessEqual(forecast["predicted_total_kw"], 25000.0)
        self.assertGreater(forecast["upper_bound_kw"], forecast["lower_bound_kw"])
        print(f"[TEST] 15-min Forecast: {forecast['predicted_total_kw']} kW (Solar: {forecast['predicted_solar_kw']} kW, Wind: {forecast['predicted_wind_kw']} kW)")

    def test_anomaly_detection_string_fault(self):
        # Normal strings
        strings = [{"string_id": f"STR-{i:02d}", "voltage_v": 850.0, "current_a": 18.5} for i in range(1, 9)]
        # Inject blown fuse on string 3
        strings[2] = {"string_id": "STR-03", "voltage_v": 0.0, "current_a": 0.0}
        
        alerts = self.anomaly_detector.evaluate_inverter_strings(
            plant_id="PLANT-SOLARIA-01",
            inverter_id="INV-02",
            strings_data=strings,
            inverter_temp_c=65.0,
            timestamp=datetime.now()
        )
        self.assertTrue(any(a["string_id"] == "STR-03" and "FUSE" in a["alert_type"] for a in alerts))
        print(f"[TEST] Anomaly Detector successfully caught blown fuse: {alerts[0]['message']}")

    def test_battery_dispatch_deficit_compensation(self):
        # Deficit scenario: Generation is 12,000 kW, Schedule is 16,000 kW (4,000 kW shortfall)
        res = self.dispatch_opt.optimize_dispatch(
            renewable_gen_kw=12000.0,
            forecast_15m_kw=13000.0,
            committed_schedule_kw=16000.0,
            current_soc_pct=70.0,
            tariff_usd_kwh=0.32
        )
        self.assertGreater(res["battery_dispatch_kw"], 3500.0)
        self.assertFalse(res["is_penalty"]) # BESS covered the deficit!
        self.assertGreater(res["penalty_avoided_usd_h"], 100.0)
        print(f"[TEST] BESS Deficit Dispatch: Discharging {res['battery_dispatch_kw']} kW, Avoided Penalty: ${res['penalty_avoided_usd_h']}/h")

    def test_full_stream_packet_processing(self):
        packet = self.simulator.generate_packet()
        enriched = self.worker.process_telemetry_packet(packet)
        self.assertIn("forecast_15m", enriched)
        self.assertIn("bess_dispatch", enriched)
        self.assertIn("financial_kpis", enriched)
        print(f"[TEST] Full Stream Enriched: Net Injected {enriched['bess_dispatch']['final_injected_kw']} kW, BESS SoC {enriched['bess_soc_pct']}%")

if __name__ == "__main__":
    unittest.main()
