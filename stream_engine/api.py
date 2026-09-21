import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from stream_engine.config import settings
from stream_engine.stream_worker import worker
from stream_engine.scenario_archive import scenario_archive
from stream_engine.models.mpc_optimizer import mpc_controller

# Pydantic schemas for disturbance triggers
class DisturbanceRequest(BaseModel):
    disturbance_type: str # 'cloud_cover', 'wind_lull', 'wind_gust', 'string_fault', 'inverter_overheat', 'tariff_spike'
    duration_sec: Optional[int] = 40
    drop_pct: Optional[float] = 75.0
    boost_pct: Optional[float] = 60.0
    inverter_id: Optional[str] = "INV-02"
    string_id: Optional[str] = "STR-03"
    fault_type: Optional[str] = "BLOWN_FUSE"
    temp_c: Optional[float] = 96.5
    tariff_usd: Optional[float] = 0.58

class AcknowledgeAlertRequest(BaseModel):
    alert_type: str
    inverter_id: Optional[str] = None
    string_id: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background streaming loop on startup
    stream_task = asyncio.create_task(worker.run_loop())
    yield
    # Cleanup on shutdown
    worker.stop()
    stream_task.cancel()

app = FastAPI(
    title="GridFlow ML Stream & Energy Prediction Engine",
    description="High-Throughput IoT Telemetry, LightGBM 15-min Yield Forecasts, & BESS Dispatch Optimization",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Vue 3 frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients
active_websockets: List[WebSocket] = []

@app.get("/api/health")
async def health_check():
    return {
        "status": "ONLINE",
        "stream_worker_running": worker.is_running,
        "model_type": worker.forecaster.model_type,
        "plant_id": settings.PLANT.plant_id,
        "capacity_mw": settings.PLANT.total_capacity_mw
    }

@app.get("/api/plant")
async def get_plant_config():
    return {
        "plant": settings.PLANT.model_dump(),
        "inverters_count": len(settings.PLANT.inverters),
        "total_strings": len(settings.PLANT.inverters) * settings.PLANT.strings_per_inverter,
        "turbines_count": len(settings.PLANT.turbines),
        "bess_capacity_mwh": settings.PLANT.bess_capacity_mwh
    }

@app.get("/api/telemetry/live")
async def get_live_telemetry():
    if not worker.last_packet:
        # Generate on-demand if loop just started
        packet = worker.simulator.generate_packet()
        return worker.process_telemetry_packet(packet)
    return worker.last_packet

@app.get("/api/telemetry/history")
async def get_telemetry_history(limit: int = 60):
    return list(worker.recent_telemetry)[-limit:]

@app.get("/api/forecast/15m")
async def get_forecast_15m():
    return {
        "latest": worker.recent_forecasts[-1] if worker.recent_forecasts else None,
        "history": list(worker.recent_forecasts)[-40:]
    }

@app.get("/api/rollups/15m")
async def get_rollups_15m():
    return list(worker.recent_rollups_15m)

@app.get("/api/inverters/health")
async def get_inverters_health():
    last = worker.last_packet
    if not last:
        return {"inverters": [], "alerts": []}
    return {
        "inverters": last["inverters"],
        "active_alerts": worker.active_alerts,
        "alerts_count": len(worker.active_alerts)
    }

@app.get("/api/alerts")
async def get_alerts():
    return {
        "active": worker.active_alerts,
        "history": list(worker.alert_history)
    }

@app.post("/api/alerts/acknowledge")
async def acknowledge_alert(req: AcknowledgeAlertRequest):
    # Mark alert as acknowledged
    for a in worker.active_alerts:
        if a["alert_type"] == req.alert_type and a.get("inverter_id") == req.inverter_id:
            a["status"] = "ACKNOWLEDGED"
    return {"status": "SUCCESS"}

@app.post("/api/simulate/disturbance")
async def trigger_disturbance(req: DisturbanceRequest):
    sim = worker.simulator
    t = req.disturbance_type.lower()
    
    if t == "cloud_cover":
        sim.trigger_cloud_cover(duration_sec=req.duration_sec, drop_pct=req.drop_pct)
        msg = f"Injected Passing Cloud: Irradiance dropped by {req.drop_pct}% for {req.duration_sec}s."
    elif t == "wind_lull":
        sim.trigger_wind_lull(duration_sec=req.duration_sec, drop_pct=req.drop_pct)
        msg = f"Injected Wind Lull: Wind speed dropped by {req.drop_pct}% for {req.duration_sec}s."
    elif t == "wind_gust":
        sim.trigger_wind_gust(duration_sec=req.duration_sec, boost_pct=req.boost_pct)
        msg = f"Injected Wind Gust: Wind speed boosted by +{req.boost_pct}% for {req.duration_sec}s."
    elif t == "string_fault":
        sim.trigger_string_fault(
            inverter_id=req.inverter_id,
            string_id=req.string_id,
            fault_type=req.fault_type
        )
        msg = f"Triggered {req.fault_type} on {req.inverter_id}:{req.string_id}."
    elif t == "inverter_overheat":
        sim.trigger_inverter_overheat(
            inverter_id=req.inverter_id,
            temp_c=req.temp_c
        )
        msg = f"Triggered thermal surge on {req.inverter_id} ({req.temp_c}°C)."
    elif t == "tariff_spike":
        sim.trigger_tariff_spike(
            tariff_usd=req.tariff_usd,
            duration_sec=req.duration_sec
        )
        msg = f"Triggered Grid Tariff Spike to ${req.tariff_usd}/kWh for {req.duration_sec}s."
    else:
        raise HTTPException(status_code=400, detail=f"Unknown disturbance type '{req.disturbance_type}'")
        
    return {
        "status": "APPLIED",
        "message": msg,
        "active_disturbances": sim.active_disturbances
    }

@app.post("/api/simulate/reset")
async def reset_disturbances():
    worker.simulator.reset_disturbances()
    return {"status": "RESET", "message": "All operational disturbances and string faults cleared."}

@app.get("/api/scenarios/catalog")
async def get_scenario_catalog():
    return scenario_archive.get_catalog()

@app.get("/api/scenarios/{scenario_id}/frames")
async def get_scenario_frames(scenario_id: str):
    frames = scenario_archive.generate_scenario_frames(scenario_id)
    return {
        "scenario_id": scenario_id,
        "total_frames": len(frames),
        "frames": frames
    }

@app.get("/api/dispatch/mpc-plan")
async def get_mpc_dispatch_plan():
    now = datetime.now()
    soc = worker.current_soc_pct
    last_p = worker.last_packet
    forecast_kw = last_p["forecast_15m"]["predicted_total_kw"] if last_p and "forecast_15m" in last_p else 18000.0
    plan = mpc_controller.optimize_4h_horizon(
        start_time=now,
        current_soc_pct=soc,
        current_forecast_p50_kw=forecast_kw
    )
    return plan

@app.post("/api/frequency/trip-generator")
async def trip_generator():
    worker.simulator.frequency_engine.trigger_generator_trip(loss_mw=1200.0)
    return {
        "status": "APPLIED",
        "message": "Simulated 1,200 MW Generator Trip: Grid frequency plunged to 59.68 Hz. Fast Frequency Response (FFR) activated."
    }

@app.post("/api/frequency/load-shed")
async def load_shed():
    worker.simulator.frequency_engine.trigger_load_shed(load_mw=800.0)
    return {
        "status": "APPLIED",
        "message": "Simulated 800 MW Load Rejection: Grid frequency surged to 60.32 Hz. Droop curtailment/charging activated."
    }

@app.post("/api/frequency/reset")
async def reset_frequency_event():
    worker.simulator.frequency_engine.reset_frequency()
    return {
        "status": "RESET",
        "message": "Grid frequency restored to nominal 60.00 Hz deadband."
    }

@app.post("/api/bess/thermal-drill")
async def trigger_bess_thermal_drill():
    worker.simulator.bess_health_engine.trigger_thermal_runaway_drill(target_rack="BESS-01:RACK-03")
    return {
        "status": "APPLIED",
        "message": "Thermal runaway drill initiated on BESS-01:RACK-03. Micro-short, off-gassing, and automated contactor trip in progress."
    }

@app.post("/api/bess/reset")
async def reset_bess_health_drill():
    worker.simulator.bess_health_engine.reset_bess_health()
    return {
        "status": "RESET",
        "message": "BESS cell health restored to nominal. DC contactors closed."
    }

@app.post("/api/drone/launch")
async def launch_drone_patrol():
    worker.simulator.drone_engine.start_mission()
    return {
        "status": "LAUNCHED",
        "message": "Autonomous Drone Patrol launched. Waypoint grid inspection in progress (35m AGL)."
    }

@app.post("/api/drone/rth")
async def drone_return_to_home():
    worker.simulator.drone_engine.abort_mission()
    return {
        "status": "RTH_COMMANDED",
        "message": "Return-to-Home (RTH) commanded. Drone returning to Substation Dock."
    }

@app.get("/api/drone/report")
async def get_drone_report():
    return worker.simulator.drone_engine.generate_inspection_report()

@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            if worker.last_packet:
                await websocket.send_text(json.dumps(worker.last_packet))
            await asyncio.sleep(settings.TELEMETRY_INTERVAL_SEC)
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
