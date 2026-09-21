# GridFlow: Project Summary & Technical Reference Guide
### Industrial-Grade IoT Telemetry, Multi-Quantile Machine Learning, Digital Twin & VPP Microgrid Platform

---

## 1. Executive Summary & Microgrid Specifications

### 1.1 Mission & Problem Statement
Large-scale renewable power plants and hybrid microgrids face severe operational, regulatory, and financial challenges:
* **Contractual Schedule Deviations**: Grid operators (e.g. CAISO, ERCOT, ENTSO-E) enforce stringent financial penalties for uninstructed deviations between day-ahead contractual commitments and real-time injected power.
* **Severe Ramp-Rate Penalties**: Rapid solar irradiance drops caused by passing cloud fronts ($R < -2.0\,\text{MW/min}$) destabilize the transmission grid, leading to regulatory fines and mandatory curtailment.
* **Asset Health & Catastrophic Risks**: High-rate cycling accelerates lithium-ion battery degradation, while undetected cell internal micro-shorts risk catastrophic thermal runaway under NFPA 855 / UL 9540A standards.
* **Local Transmission Congestion**: Feeder line bottlenecks require real-time Locational Marginal Pricing (LMP) and Peer-to-Peer (P2P) trading across Virtual Power Plants (VPPs) to balance supply and demand locally.

**GridFlow** is an end-to-end industrial SCADA, predictive machine learning, and autonomous control platform engineered for **Solaria West (Mojave High-Desert Microgrid)** and its regional Virtual Power Plant partners.

---

### 1.2 Solaria West Microgrid Physical Specifications
* **Location**: Mojave Desert, California ($35.0110^\circ\text{N}, 115.4734^\circ\text{W}$, Elevation: 745 m)
* **Total Nameplate Capacity**: **25.0 MW** Hybrid Microgrid
  * **Solar PV Array**: 20.0 MW DC (4 Central Inverter blocks of 5.0 MW each)
    * 32 Total Inverter Strings (8 strings per inverter, 850 V DC nominal, 18.5 A per string, 20 bifacial monocrystalline PERC modules per string)
    * Single-Axis Horizontal Trackers with astronomical backtracking ($GCR = 0.40$)
  * **Wind Generation**: 5.0 MW AC (2 $\times$ 2.5 MW Variable-Speed Pitch-Regulated Turbines, 100m hub height, 115m rotor diameter)
  * **Battery Energy Storage System (BESS)**: 10.0 MWh / 5.0 MW Lithium Iron Phosphate (LFP)
    * 4 Containerized Megapacks, 16 Racks total (850 V DC nominal bus)
    * C-Rate: 0.5C continuous / 1.0C peak (Fast Frequency Response)
  * **Interconnection**: 34.5 kV Collector System $\rightarrow$ 230 kV Utility Substation Interconnection

---

### 1.3 Regional VPP Aggregated Fleet Portfolio
GridFlow aggregates Solaria West with three nearby industrial prosumers into a 43.5 MW Virtual Power Plant:
1. **Solaria West Microgrid (Anchor Prosumer)**: 25.0 MW generation + 10 MWh storage.
2. **Mojave Green Hydrogen Electrolyzer (Flexible Load)**: 8.0 MW PEM electrolyzer with 12-hour $H_2$ buffer storage (flexible dispatch between 2.0 MW idle and 8.0 MW full absorption).
3. **Boron Lithium Processing Facility (Critical Baseload)**: 6.5 MW continuous chemical extraction facility with high willingness to pay to prevent refinery downtime. Subject to transmission congestion on Feeder 3.
4. **Mojave Compute AI Center (Curtailable Load)**: 4.0 MW IT load with 2.5 MW critical cooling/inference and 1.5 MW curtailable batch model training workloads.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Layer1["1. High-Frequency IoT Ingestion (2-Second Ticks)"]
        PV["32 PV Strings (850V, 18.5A)"] --> Inverters["4 Central Inverters (5 MW)"]
        WTG["2 Wind Turbines (2.5 MW)"] --> Inverters
        Sensors["Pyranometers, Anemometers, Off-Gas (H2/CO)"] --> Inverters
        Inverters --> Broker["Mosquitto MQTT (1883) / Kafka KRaft (9092)"]
    end

    subgraph Layer2["2. Python Stream Engine & Specialized Models (FastAPI)"]
        Broker --> Worker["Asynchronous Stream Worker"]
        Worker --> QForecaster["Multi-Quantile LightGBM (P10 / P50 / P90)"]
        Worker --> MPCOptimizer["4-Hour MPC HiGHS Linear Programming"]
        Worker --> TrackerEng["Astronomical Backtracking Engine (GCR = 0.40)"]
        Worker --> SkyRadar["All-Sky Cloud Motion Optical Flow (Ramp-Rate)"]
        Worker --> FreqDroop["Fast Frequency Response (FFR) & Inertia (s=4%, H=4.5s)"]
        Worker --> BessHealth["2RC Thevenin ECM & NFPA 855 Thermal Runaway"]
        Worker --> DronePatrol["Autonomous FLIR Radiometric Drone Patrol (IEC 62446-3)"]
        Worker --> VPPTrading["Continuous Double-Auction & P2P Trading Engine"]
    end

    subgraph Layer3["3. Time-Series Storage & Aggregation"]
        Worker --> Timescale["TimescaleDB / PostgreSQL 16"]
        Timescale --> Rollup15m["telemetry_15m Continuous Hypertables"]
        Timescale --> Rollup1h["telemetry_1h Continuous Hypertables"]
    end

    subgraph Layer4["4. Laravel 12 Backend & CMMS Work Orders"]
        Worker --> Redis["Redis Queue / Event Bus"]
        Redis --> Laravel["Laravel 12 API Engine (PHP 8.2)"]
        Laravel --> Topology["Plant & Inverter String Registry"]
        Laravel --> WorkOrders["CMMS Work Orders & Multimeter Checklists"]
    end

    subgraph Layer5["5. Industrial SCADA Web Operator Console"]
        Worker -.->|WebSocket /ws/stream (2s)| SCADA_UI["Vue 3 + Vite SCADA"]
        SCADA_UI --> Map["Leaflet Spatial Map"]
        SCADA_UI --> FanChart["ECharts Probabilistic Fan Chart"]
        SCADA_UI --> Twin3D["Three.js 3D WebGL Digital Twin"]
        SCADA_UI --> SkyCam["Fisheye Sky Radar (CMV)"]
        SCADA_UI --> Osc["Dual-Trace High-Speed Frequency Oscilloscope"]
        SCADA_UI --> BessDiag["16-Rack Cell Matrix & EIS Nyquist Plot"]
        SCADA_UI --> FLIR["FLIR Radiometric Viewfinder (Ironbow)"]
        SCADA_UI --> VPPDash["Merit-Order Order Book & REC Token Ledger"]
        Laravel -.->|REST API| SCADA_UI
    end
```

---

## 3. The 10 Advanced Engineering Modules

### Module 1: Probabilistic Multi-Quantile Yield Forecaster ($P_{10}, P_{50}, P_{90}$)
* **File**: [`stream_engine/models/yield_forecaster.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/yield_forecaster.py)
* **Mathematical Concept**: Pinball loss minimization for quantile regression:
  $$\mathcal{L}_q(y, \hat{y}) = \max(q(y - \hat{y}), (1 - q)(\hat{y} - y))$$
* **Renewable Market Semantics**:
  * **$P_{90}$ (Conservative Floor)**: Exceeded 90% of the time. Used for penalty-free grid bidding.
  * **$P_{50}$ (Expected Value)**: 50% probability midpoint for baseline operational planning.
  * **$P_{10}$ (High-Yield Upside)**: 10% probability ceiling for surplus battery charging.
* **Guarantee**: Enforces strict quantile monotonicity ($P_{10} \ge P_{50} \ge P_{90}$).

### Module 2: Historical Time-Machine & Incident Playback Engine
* **File**: [`stream_engine/scenario_archive.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/scenario_archive.py)
* **Capabilities**: Frame-by-frame historical scrubber (1x, 2x, 4x speed) with deep replay states.
* **Archived Incident Scenarios**:
  * `INC-2026-041`: Passing cumulus cloud front causing sudden -70% solar drop in 40 seconds.
  * `INC-2026-088`: Combiner box blown fuse on `INV-02:STR-03` with immediate voltage collapse to 0.0V.
  * `INC-2026-112`: 1,200 MW regional generator trip causing grid frequency to plunge to 59.68 Hz.

### Module 3: Automated CMMS Work Order Dispatcher
* **Files**: [`backend/app/Http/Controllers/WorkOrderController.php`](file:///d:/xampp/htdocs/Grid%20Flow/backend/app/Http/Controllers/WorkOrderController.php), [`backend/app/Models/WorkOrder.php`](file:///d:/xampp/htdocs/Grid%20Flow/backend/app/Models/WorkOrder.php)
* **Capabilities**:
  * String divergence trigger: Automatically dispatches work orders when string voltage deviates by $>12\%$ from inverter median.
  * Generates digital multimeter checklists: Open-circuit voltage ($V_{oc}$), short-circuit current ($I_{sc}$), insulation resistance ($R_{iso} > 1.0\,\text{M}\Omega$), and terminal torque checks ($18.0\,\text{N}\cdot\text{m}$).
  * Dispatches automated technician notifications via queue worker.

### Module 4: 4-Hour Model Predictive Control (MPC) Battery Dispatch
* **File**: [`stream_engine/models/mpc_optimizer.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/mpc_optimizer.py)
* **Solver**: High-performance simplex / interior-point linear programming via `scipy.optimize.linprog(method="highs")`.
* **Lookahead**: 4 hours ($T = 16$ time steps, $\Delta t = 15\,\text{min}$).
* **Objective Function**:
  $$\max \sum_{t=1}^{T} \left( \pi_t P_t^{\text{grid}} \Delta t - C_{\text{penalty}} \max(0, P_t^{\text{committed}} - P_t^{\text{grid}}) \Delta t - C_{\text{deg}} |P_t^{\text{bess}}| \Delta t \right)$$
  subject to:
  * $SOC_{\min} \le SOC_t \le SOC_{\max}$ ($10\% \le SOC \le 90\%$)
  * $-P_{\text{chg}}^{\max} \le P_t^{\text{bess}} \le P_{\text{dis}}^{\max}$ ($5,000\,\text{kW}$)
  * Battery degradation cost: $C_{\text{deg}} \approx \$0.022/\text{kWh}$.

### Module 5: 3D Digital Twin & Astronomical Solar Tracker
* **Files**: [`stream_engine/models/solar_tracker.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/solar_tracker.py), [`frontend/src/components/DigitalTwinModal.vue`](file:///d:/xampp/htdocs/Grid%20Flow/frontend/src/components/DigitalTwinModal.vue)
* **3D WebGL Engine**: Complete Three.js scene with 32 motorized PV tracker tables, 2 wind turbines, 4 BESS Megapacks, and 230kV substation.
* **Astronomical Backtracking ($GCR = 0.40$)**:
  $$\theta_{\text{backtrack}} = \arcsin\left(\frac{\sin \theta_{\text{true}}}{GCR}\right)$$
* **Visual Modes**: PBR Standard Shading, Radiometric Thermal IR, and Electrical Fault Highlight.

### Module 6: All-Sky Cloud Motion Vector (CMV) & Ramp-Rate Engine
* **File**: [`stream_engine/models/cloud_motion.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/cloud_motion.py)
* **Algorithm**: Polar fisheye sky camera simulation with Lucas-Kanade optical flow.
* **Ground Shadow Projection**: Projects approaching cloud shadows onto the 250m microgrid radius to calculate Time-to-Impact (TTI).
* **Ramp Smoothing**: Pre-activates BESS fast-ramp buffer when predicted ramp rate $R < -2.0\,\text{MW/min}$, holding net injection drop to $<0.5\,\text{MW/min}$.

### Module 7: Fast Frequency Response (FFR), Synthetic Inertia & Droop Control
* **File**: [`stream_engine/models/frequency_droop.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/frequency_droop.py)
* **Governing Dynamics**:
  * **Synthetic Inertia**: $P_{\text{inertia}} = -2H \frac{df}{dt}$ ($H = 4.5\,\text{s}$).
  * **Primary Frequency Droop**: $s = 4.0\%$ with $\pm 0.036\,\text{Hz}$ deadband.
  * **Fast Frequency Response (FFR)**: Instantaneous sub-second $+5.0\,\text{MW}$ burst if $f < 59.70\,\text{Hz}$.
* **SCADA UI**: Dual-trace high-speed oscilloscope recording grid frequency and BESS response.

### Module 8: BESS Battery Health (SOH) & NFPA 855 Thermal Runaway Early Warning
* **File**: [`stream_engine/models/battery_health.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/battery_health.py)
* **Electrochemical Modeling**: 2RC Thevenin ECM ($R_0$ ohmic resistance, $R_1 C_1$ charge transfer, $R_2 C_2$ diffusion polarization).
* **Safety Protocol (NFPA 855 / UL 9540A)**:
  * Stage 1: Thermal Overstress ($T > 45^\circ\text{C}$).
  * Stage 2: Micro-Short & Rapid Voltage Sag.
  * Stage 3: Off-Gas Detection ($H_2 > 20\,\text{ppm}, CO > 15\,\text{ppm}$).
  * Stage 4: Thermal Propagation & Automated DC Contactor Trip.
* **SCADA UI**: 16-rack cell matrix heatmap and Electrochemical Impedance Spectroscopy (EIS) Nyquist plot.

### Module 9: Autonomous Drone Aerial Thermography & IEC 62446-3 Defect Classifier
* **File**: [`stream_engine/models/drone_inspection.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/drone_inspection.py)
* **Flight Engine**: 16-waypoint autonomous lawnmower patrol at 35m AGL.
* **IEC 62446-3 Classification**:
  * Class 1 ($\Delta T < 10^\circ\text{C}$): Minor anomaly / monitoring.
  * Class 2 ($10 \le \Delta T \le 30^\circ\text{C}$): Hotspot / bypass diode open-circuit.
  * Class 3 ($\Delta T > 30^\circ\text{C}$): Critical fire hazard / cell fracture.
* **SCADA UI**: Radiometric FLIR viewfinder with Ironbow false-color palette, crosshair spot meter, and automated inspection report generator.

### Module 10: Virtual Power Plant (VPP) Aggregation & P2P Microgrid Trading
* **File**: [`stream_engine/models/vpp_trading.py`](file:///d:/xampp/htdocs/Grid%20Flow/stream_engine/models/vpp_trading.py)
* **Market Clearing**: Continuous double-auction merit-order clearing calculating Market Clearing Price (MCP), cleared volume, and consumer/producer surplus.
* **Locational Marginal Pricing (LMP)**:
  $$\text{LMP}_i = \text{MCP} + \text{Congestion Surcharge}_i + \text{Loss Factor}_i \times \text{MCP}$$
* **Carbon Provenance**: Mints cryptographic **Renewable Energy Certificates (REC tokens)** with SHA-256 origin proofs (`0x...`) and $0.385\,\text{tCO}_2/\text{MWh}$ avoided emissions tracking.

---

## 4. Codebase Navigation & Directory Topology

```
d:\xampp\htdocs\Grid Flow\
├── start_all.bat                   # Master Windows one-click launcher
├── start_stream_engine.bat         # Python FastAPI service launcher
├── start_backend.bat               # Laravel 12 backend launcher
├── start_frontend.bat              # Vue 3 SCADA launcher
├── run_tests.bat                   # 34-unit-test suite runner
├── build_frontend.bat              # Vite production bundle compiler
├── README.md                       # High-level overview & quickstart
├── PROJECT_SUMMARY_AND_REFERENCE_GUIDE.md # This document
│
├── stream_engine/                  # Python Stream Engine & ML Core
│   ├── api.py                      # FastAPI REST API & WebSocket endpoints
│   ├── config.py                   # Microgrid physical ratings & topology config
│   ├── simulator.py                # 2s IoT Telemetry Simulator with all 10 sub-engines
│   ├── stream_worker.py            # Async streaming processor and rollups
│   ├── scenario_archive.py         # Incident replayer with frame caches
│   ├── models/
│   │   ├── yield_forecaster.py     # Multi-quantile LightGBM (P10, P50, P90)
│   │   ├── anomaly_detector.py     # Inverter string voltage divergence detector
│   │   ├── dispatch_optimizer.py   # Baseline battery dispatch optimizer
│   │   ├── mpc_optimizer.py        # 4-hour forward lookahead HiGHS LP optimizer
│   │   ├── solar_tracker.py        # Astronomical sun positioning & backtracking
│   │   ├── cloud_motion.py         # All-sky fisheye camera optical flow & ramp buffer
│   │   ├── frequency_droop.py      # FFR, synthetic inertia & droop engine
│   │   ├── battery_health.py       # 2RC Thevenin ECM & NFPA 855 thermal runaway
│   │   ├── drone_inspection.py     # Autonomous drone patrol & IEC 62446-3 classifier
│   │   └── vpp_trading.py          # Continuous double-auction & P2P trading engine
│   └── tests/                      # 34 Automated Unit Tests
│       ├── test_stream.py          # Core stream, LightGBM, and dispatch tests
│       ├── test_mpc.py             # HiGHS LP solver tests
│       ├── test_solar_tracker.py   # Backtracking and elevation tests
│       ├── test_cloud_motion.py    # Cloud motion vector and ramp tests
│       ├── test_frequency_droop.py # Frequency response and inertia tests
│       ├── test_battery_health.py  # ECM voltage and thermal runaway drill tests
│       ├── test_drone_inspection.py# Drone flight and defect grading tests
│       ├── test_vpp_trading.py     # Merit-order clearing and REC token tests
│       └── test_scenarios.py       # Incident playback frame tests
│
├── backend/                        # Laravel 12 CMMS & SCADA API
│   ├── app/Models/                 # Plant, Inverter, InverterString, BessUnit, WorkOrder
│   ├── app/Http/Controllers/       # PlantController, AlertController, WorkOrderController
│   ├── app/Jobs/                   # DispatchWorkOrderNotificationJob
│   ├── database/migrations/        # Schema migrations for CMMS and microgrid topology
│   └── routes/api.php              # Laravel REST API routes
│
└── frontend/                       # Vue 3 + Vite SCADA Operator Console
    ├── src/
    │   ├── App.vue                 # SCADA Root Layout & Navigation Coordinator
    │   ├── components/
    │   │   ├── PlantMap.vue        # Leaflet Geospatial Microgrid Layout Map
    │   │   ├── ForecastCurve.vue   # ECharts Probabilistic Fan Chart (P10/P50/P90)
    │   │   ├── BessPowerFlow.vue   # Radial BESS SoC Gauge & Dispatch Setpoints
    │   │   ├── StringMonitor.vue   # 32 PV String Divergence Heatmap Matrix
    │   │   ├── TariffArbitrage.vue # Real-Time TOU Pricing & Revenue Counter
    │   │   ├── AlertFeed.vue       # 4-Tier SCADA Alert Feed with Tech Dispatch
    │   │   ├── ScenarioControl.vue # Operator Disturbance Injection Controls
    │   │   ├── PlaybackController.vue # Time-Machine Historical Incident Scrubber
    │   │   ├── MpcTrajectoryModal.vue # 4-Hour Forward Lookahead MPC Horizon Modal
    │   │   ├── WorkOrdersModal.vue # Slide-Over CMMS Technician Work Order Drawer
    │   │   ├── DigitalTwinModal.vue# Full Three.js 3D WebGL Digital Twin
    │   │   ├── SkyCamRadar.vue     # Polar Fisheye Sky Radar & Optical Flow Vectors
    │   │   ├── FrequencyResponse.vue # High-Speed Dual-Trace Oscilloscope & FFR
    │   │   ├── BessHealthModal.vue # 16-Rack Matrix Heatmap & EIS Nyquist Plot
    │   │   ├── DroneMissionModal.vue # Radiometric FLIR Thermal Viewfinder (Ironbow)
    │   │   └── VppTradingModal.vue # Merit-Order Order Book & REC Token Ledger
    │   └── assets/main.css         # Industrial SCADA Design Tokens & Aesthetics
    └── package.json
```

---

## 5. Telemetry Data Dictionary (2-Second Packet)

| Key Path | Type | Unit | Range | Description |
|---|---|---|---|---|
| `timestamp` | String (ISO) | - | - | UTC Timestamp of the telemetry tick |
| `plant_id` | String | - | - | Unique plant identifier (`SOLARIA-WEST-01`) |
| `weather.irradiance_wm2` | Float | $\text{W/m}^2$ | $0.0 - 1200.0$ | Plane-of-Array Solar Irradiance |
| `weather.wind_speed_ms` | Float | $\text{m/s}$ | $0.0 - 30.0$ | Anemometer Wind Speed at 100m hub |
| `weather.ambient_temp_c` | Float | $^\circ\text{C}$ | $-10.0 - 55.0$ | Ambient Desert Temperature |
| `weather.module_temp_c` | Float | $^\circ\text{C}$ | $-10.0 - 85.0$ | Back-of-Module Temperature (PV cells) |
| `solar_generation_kw` | Float | $\text{kW}$ | $0.0 - 20000.0$ | Total Solar AC Power Injected |
| `wind_generation_kw` | Float | $\text{kW}$ | $0.0 - 5000.0$ | Total Wind Turbine Generation |
| `total_renewable_kw` | Float | $\text{kW}$ | $0.0 - 25000.0$ | Solar + Wind Real-Time Total |
| `committed_schedule_kw`| Float | $\text{kW}$ | $0.0 - 20500.0$ | Contractual Committed Generation Curve |
| `tariff_usd_kwh` | Float | $\$ / \text{kWh}$ | $0.06 - 0.58$ | Dynamic Time-of-Use Grid Tariff |
| `bess_soc_pct` | Float | $\%$ | $0.0 - 100.0$ | Battery State of Charge |
| `spatial_tracking` | Object | - | - | Sun elevation, azimuth, tracker angle, backtracking status |
| `cloud_tracking` | Object | - | - | Cloud speed, heading, TTI (sec), predicted ramp rate ($\text{MW/min}$) |
| `frequency_response` | Object | - | - | Grid frequency ($\text{Hz}$), $df/dt$, synthetic inertia ($\text{kW}$), droop ($\text{kW}$) |
| `bess_health` | Object | - | - | 2RC ECM terminal voltage, SOH capacity %, off-gas sensors ($H_2, CO$), contactor status |
| `drone_inspection` | Object | - | - | Drone waypoint coordinates, altitude, battery %, FLIR temperature matrix, defects |
| `vpp_trading` | Object | - | - | Market clearing price ($\$ / \text{MWh}$), cleared volume ($\text{MW}$), order book, REC tokens |
| `inverters` | Array[4] | - | - | Individual inverter AC/DC kW, temperatures, and 32 string voltages/currents |
| `turbines` | Array[2] | - | - | Individual turbine power ($\text{kW}$), wind speed, and rotor RPM |

---

## 6. Comprehensive API Reference Guide

### 6.1 Telemetry & Forecasts
* **`GET /api/health`**: Returns service status, worker state, model type, and capacity.
* **`GET /api/telemetry/live`**: Returns latest comprehensive 2-second telemetry packet.
* **`GET /api/telemetry/history?limit=60`**: Returns rolling buffer of past telemetry packets.
* **`GET /api/forecast/15m`**: Returns latest LightGBM multi-quantile prediction ($P_{10}, P_{50}, P_{90}$).
* **`GET /api/rollups/15m`**: Returns 15-minute TimescaleDB continuous aggregates.
* **`WS /ws/stream`**: Continuous WebSocket emitting the live telemetry packet every 2 seconds.

### 6.2 Optimization & Control
* **`GET /api/dispatch/mpc-plan`**: Generates a 4-hour forward lookahead HiGHS LP battery dispatch trajectory.
* **`POST /api/simulate/disturbance`**: Injects operational disturbances:
  * Schema: `{ disturbance_type: 'cloud_cover' | 'wind_lull' | 'wind_gust' | 'string_fault' | 'inverter_overheat' | 'tariff_spike', duration_sec: 40, drop_pct: 75.0, inverter_id: 'INV-02', string_id: 'STR-03' }`
* **`POST /api/simulate/reset`**: Clears all active disturbances and restores normal simulation.

### 6.3 Specialized Engineering Drills
* **`POST /api/frequency/trip-generator`**: Triggers a simulated 1,200 MW generator loss ($f \rightarrow 59.68\,\text{Hz}$).
* **`POST /api/frequency/load-shed`**: Triggers a simulated 800 MW load rejection ($f \rightarrow 60.32\,\text{Hz}$).
* **`POST /api/frequency/reset`**: Restores grid frequency to nominal 60.00 Hz deadband.
* **`POST /api/bess/thermal-drill`**: Initiates NFPA 855 thermal runaway drill and contactor trip on `BESS-01:RACK-03`.
* **`POST /api/bess/reset`**: Restores BESS cell health and closes DC contactors.
* **`POST /api/drone/launch`**: Launches autonomous FLIR drone patrol along the 16-waypoint inspection grid.
* **`POST /api/drone/rth`**: Commands the drone to return to the substation dock.
* **`GET /api/drone/report`**: Generates a comprehensive IEC 62446-3 aerial thermal inspection report.

### 6.4 Virtual Power Plant (VPP) Trading
* **`GET /api/vpp/orderbook`**: Returns current sorted bids, asks, Market Clearing Price (MCP), and cleared volume.
* **`GET /api/vpp/assets`**: Returns real-time status, power, marginal costs/bids, and nodal LMPs for all 4 VPP nodes.
* **`GET /api/vpp/transactions`**: Returns recent settled P2P bilateral trades with cryptographic REC token hashes.
* **`POST /api/vpp/action`**: Injects market events:
  * Schema: `{ action: 'electrolyzer_surge' | 'datacenter_curtailment' | 'peak_arbitrage', mw: 3.2, price: 48.0 }`
* **`POST /api/vpp/reset`**: Restores VPP market to auto-balancing mode.

---

## 7. SCADA Operator Runbook

### 7.1 Standard Monitoring Operations
1. **Header Metrics Strip**: Monitor real-time net injected power, 15-minute LightGBM forecast, $P_{90}$ conservative floor, committed schedule, grid frequency, ramp rate, and BESS SoC.
2. **Plant Map**: Observe inverter status pins. Red pin indicates string voltage divergence or inverter thermal fault.
3. **Forecast Curve**: Inspect the probabilistic fan chart. Green curve represents actual injection; cyan dashed line represents $P_{50}$ forecast; shaded envelope shows $P_{10} - P_{90}$ confidence interval.
4. **String Monitor**: Check the 32-string divergence matrix. Normal strings display green (~850V); faulted strings display red (0V).

### 7.2 Handling Alarms & Work Orders
1. When an inverter string fault occurs, an alert appears in the **Alert Feed**.
2. Click **"Dispatch Tech"** on the alert. This opens the **Work Orders Drawer** and automatically provisions a new CMMS work order with technician assignment and multimeter checklist.
3. Once the field technician enters multimeter values ($V_{oc}, I_{sc}, R_{iso}$), mark the work order as `COMPLETED`.

### 7.3 Operating the 3D Digital Twin
1. Click **"3D Digital Twin"** in the SCADA header.
2. Use mouse orbit controls (Left-click to rotate, Right-click to pan, Scroll to zoom).
3. Toggle visual modes:
   * **PBR Shading**: Realistic lighting and shadows.
   * **Thermal IR**: False-color temperature rendering of panels, inverters, and Megapacks.
   * **Fault Highlight**: Pulses faulted components in neon red.
4. Click any tracker table or inverter to display raycasted telemetry in the HUD.

### 7.4 Conducting Safety & Market Drills
* **Ramp-Rate Smoothing**: Click "Passing Cloud" in the Scenario Control widget. Observe the All-Sky SkyCam Radar track the cloud shadow and the BESS fast-ramp buffer prime to prevent ramp rate violation.
* **Grid Frequency Event**: Click "Simulate 1,200 MW Gen Trip" in the Frequency Response widget. Observe the dual-trace oscilloscope track the frequency plunge to 59.68 Hz and the sub-second +5 MW FFR injection.
* **Thermal Runaway Drill**: Open "SOH & Safety" from the BESS widget. Click "Trigger Thermal Runaway Drill". Watch cell temperature rise, off-gas sensors ($H_2, CO$) trigger alarms, and the DC contactor automatically trip to isolate Rack 03.
* **VPP Energy Trading**: Click "VPP P2P Trading" in the header. Review the order book and market depth step curve. Click "Electrolyzer Surge Buy" to simulate increased green hydrogen demand, observe MCP adjust, and verify the newly minted SHA-256 REC token.

---

## 8. Developer & Deployment Operations Manual

### 8.1 Windows One-Click Quickstart
Double-click:
```bat
start_all.bat
```
This automatically initializes the Python FastAPI stream engine (Port 8000), Laravel 12 backend (Port 8080), and Vue 3 SCADA frontend (Port 5173) in dedicated console windows and opens `http://localhost:5173` in your browser.

### 8.2 Manual Startup Commands
* **Python Stream Engine**:
  ```powershell
  python -m uvicorn stream_engine.api:app --host 127.0.0.1 --port 8000 --reload
  ```
* **Laravel Backend**:
  ```powershell
  cd backend
  php artisan serve --port 8080
  ```
* **Vue 3 SCADA Frontend**:
  ```powershell
  cd frontend
  npm.cmd run dev
  ```

### 8.3 Running Automated Tests
```powershell
python -m unittest discover stream_engine/tests -v
```
*(Or double-click `run_tests.bat`)* — Executes 34 unit tests verifying all 10 engineering modules.

### 8.4 Production Frontend Compilation
```powershell
cd frontend
npm.cmd run build
```
*(Or double-click `build_frontend.bat`)* — Compiles optimized production bundle via Vite with 0 errors.

---

## 9. Industry Standards & Compliance Matrix

| Standard | Scope | GridFlow Implementation |
|---|---|---|
| **IEEE 1547-2018** | DER Interconnection & Interoperability | $s = 4.0\%$ droop slope, $\pm 0.036\,\text{Hz}$ deadband, FFR sub-second injection |
| **IEC 61724-1:2021** | PV Performance Monitoring (Class A) | 2-second high-speed sampling, POA/GHI sensors, $\gamma = -0.38\%/^\circ\text{C}$ derating |
| **IEC 62446-3:2017** | Outdoor Infrared Thermography | Class 1, 2, and 3 defect grading from radiometric FLIR aerial drone data |
| **NFPA 855 / UL 9540A**| Stationary Energy Storage Safety | 4-stage thermal runaway warning, $H_2/CO$ off-gas detection, automated DC contactor trip |
| **IEC 61400-12-1:2017**| Wind Turbine Power Measurement | Cubic power curve modeling between $3\,\text{m/s}$ cut-in and $12\,\text{m/s}$ rated speed |
| **CAISO / NERC BAL-001**| Real-Time Frequency & Ramp Rates | Synthetic inertia ($H = 4.5\,\text{s}$), $-2.0\,\text{MW/min}$ ramp limit enforcement |
| **FERC 2222 / WREGIS** | Distributed Energy & Carbon Accounting | Double-auction merit-order clearing, nodal LMPs, SHA-256 REC origin proofs |
| **ISA-101 / EEMUA 191** | HMI & Alarm Systems Design | Cyber-dark fatigue-reducing UI, semantic color coding, monospace data readouts |

---

## 10. Cybersecurity & OT Hardening Roadmap

To transition GridFlow from demonstration mode to a live utility-scale substation deployment, adhere to the following **IEC 62443** and **NERC CIP** hardening roadmap:

1. **Network Segmentation (Purdue Model / IEC 62443-3-2)**:
   * **Level 1 (Field Devices)**: Inverters, BESS racks, and pyranometers must communicate over isolated OT VLANs using encrypted Modbus TCP or private MQTTS (Port 8883) with **Mutual TLS (mTLS)**.
   * **Level 2 (Supervisory Control)**: Python Stream Engine and TimescaleDB inside an Electronic Security Perimeter (ESP) per **NERC CIP-005**.
   * **Level 3 (Operations / CMMS)**: Laravel 12 API behind an internal DMZ.
   * **Level 4 (SCADA UI)**: Protected by an Envoy/Nginx reverse proxy terminating TLS 1.3 with strict domain CORS.
2. **Authentication & RBAC (IEC 62443-3-3 SR 1.1 / 1.2)**:
   * Enforce JWT / Bearer token authentication with Role-Based Access Control:
     * `Viewer`: Read-only access to telemetry, forecasts, and 3D digital twin.
     * `Operator`: Acknowledge alerts, dispatch work orders, and submit P2P bids.
     * `Safety Engineer`: Multi-Factor Authentication (MFA) required for physical/simulation drill actuation (generator trip, DC contactor trip).
3. **Command Non-Repudiation & Audit Logging (NERC CIP-007 / CIP-008)**:
   * Record all operator interventions in an immutable append-only audit log signed with digital cryptographic signatures.
