<template>
  <div v-if="isOpen" class="modal-backdrop" @keydown.esc="close" tabindex="0">
    <div class="modal-card">
      <!-- Header -->
      <div class="modal-header">
        <div class="modal-title-wrap">
          <div class="modal-icon-wrap">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber"><polygon points="12 2 19 21 12 17 5 21 12 2"/></svg>
          </div>
          <div>
            <div class="modal-title">
              AUTONOMOUS DRONE THERMOGRAPHY <span class="text-amber">// AERIAL FLIR INSPECTION (IEC 62446-3)</span>
            </div>
            <div class="modal-subtitle">
              DJI Matrice 350 RTK • Zenmuse H20T Radiometric IR • 35m AGL Lawnmower Grid
            </div>
          </div>
        </div>

        <!-- Telemetry Badges -->
        <div class="header-badges">
          <div class="h-badge" :class="stateBadgeClass">
            <span class="hb-lbl">MISSION STATE</span>
            <span class="hb-val">{{ droneState }}</span>
          </div>
          <div class="h-badge">
            <span class="hb-lbl">ALTITUDE</span>
            <span class="hb-val mono-val text-cyan">{{ (droneData?.position?.z_alt_m || 0).toFixed(1) }} m AGL</span>
          </div>
          <div class="h-badge">
            <span class="hb-lbl">DRONE BATTERY</span>
            <span class="hb-val mono-val" :class="batteryPct < 25 ? 'text-rose' : 'text-emerald'">{{ Math.round(batteryPct) }}%</span>
          </div>
          <div class="h-badge" :class="defectsCount > 0 ? 'badge-rose' : 'badge-slate'">
            <span class="hb-lbl">DEFECTS FOUND</span>
            <span class="hb-val mono-val">{{ defectsCount }}</span>
          </div>
          <button @click="close" class="modal-close-btn">&times;</button>
        </div>
      </div>

      <!-- Main Body -->
      <div class="modal-body">
        <!-- Left: Radiometric Thermal FLIR Viewfinder -->
        <div class="viewfinder-col">
          <div class="flir-viewport">
            <!-- Tactical Crosshairs & HUD Elements -->
            <div class="flir-hud-top">
              <span class="flir-tag">FLIR RADIOMETRIC // IRONBOW</span>
              <span class="flir-emissivity mono-val">ε = 0.88 • T_refl: 22.0°C</span>
              <span class="flir-rec" :class="{ active: droneState === 'INSPECTING' }">● REC</span>
            </div>

            <!-- Thermal Canvas Background -->
            <div class="thermal-screen">
              <!-- Center Spot Meter Crosshair -->
              <div class="crosshair-wrap">
                <div class="crosshair-ch"></div>
                <div class="spot-temp-pill mono-val" :class="spotTemp > 55 ? 'pill-hot' : 'pill-norm'">
                  {{ spotTemp.toFixed(1) }}°C
                </div>
              </div>

              <!-- Defect Bounding Boxes in Frame -->
              <div 
                v-for="(defect, idx) in defectsInView" 
                :key="idx" 
                class="defect-bbox"
                :style="{
                  left: `${defect.bbox[0]}px`,
                  top: `${defect.bbox[1]}px`,
                  width: `${defect.bbox[2] - defect.bbox[0]}px`,
                  height: `${defect.bbox[3] - defect.bbox[1]}px`
                }"
              >
                <div class="bbox-label">
                  <span class="b-type">{{ defect.type }}</span>
                  <span class="b-temp mono-val">{{ defect.spot_temp_c }}°C</span>
                </div>
              </div>

              <!-- Thermal Legend Bar -->
              <div class="flir-temp-scale">
                <span class="scale-stop">85°C</span>
                <div class="scale-bar"></div>
                <span class="scale-stop">20°C</span>
              </div>
            </div>

            <!-- FLIR Bottom Bar -->
            <div class="flir-hud-bottom">
              <span>FOV: 40.6° • 640x512 Radiometric</span>
              <span class="mono-val text-cyan">SPOT: {{ spotTemp.toFixed(1) }}°C • AMB: {{ ambientTemp.toFixed(1) }}°C</span>
              <span>WP: {{ currentWp }}</span>
            </div>
          </div>

          <!-- Mission Command Bar -->
          <div class="mission-actions">
            <button 
              @click="launchMission" 
              class="btn-m btn-launch" 
              :disabled="isActing || droneState === 'INSPECTING'"
            >
              🚀 Launch Autonomous Patrol
            </button>
            <button 
              @click="returnHome" 
              class="btn-m btn-rth" 
              :disabled="isActing || droneState === 'DOCKED'"
            >
              🏠 Return to Home (RTH)
            </button>
            <button 
              @click="showReport = !showReport" 
              class="btn-m btn-report"
            >
              📄 {{ showReport ? 'Hide Report' : 'IEC 62446-3 Report' }}
            </button>
          </div>
        </div>

        <!-- Right: Flight Path Radar & Defect Catalog -->
        <div class="flight-col">
          <!-- Waypoint Flight Radar -->
          <div class="flight-radar-card">
            <div class="card-inner-header">
              <span class="card-inner-title">SOLARIA WEST WAYPOINT FLIGHT PATH</span>
              <span class="card-inner-sub mono-val text-cyan">Progress: {{ missionProgress }}%</span>
            </div>

            <!-- Flight Path Map SVG -->
            <div class="radar-svg-wrap">
              <svg class="flight-svg" viewBox="-110 -80 230 160">
                <!-- Zone Outlines -->
                <!-- INV-01 -->
                <rect x="-85" y="-60" width="45" height="40" fill="rgba(6, 182, 212, 0.05)" stroke="rgba(6, 182, 212, 0.2)" rx="3" />
                <text x="-80" y="-48" class="zone-txt">INV-01</text>
                <!-- INV-02 -->
                <rect x="15" y="-60" width="45" height="40" fill="rgba(6, 182, 212, 0.05)" stroke="rgba(6, 182, 212, 0.2)" rx="3" />
                <text x="20" y="-48" class="zone-txt">INV-02</text>
                <!-- INV-03 -->
                <rect x="-85" y="20" width="45" height="40" fill="rgba(6, 182, 212, 0.05)" stroke="rgba(6, 182, 212, 0.2)" rx="3" />
                <text x="-80" y="32" class="zone-txt">INV-03</text>
                <!-- INV-04 -->
                <rect x="15" y="20" width="45" height="40" fill="rgba(6, 182, 212, 0.05)" stroke="rgba(6, 182, 212, 0.2)" rx="3" />
                <text x="20" y="32" class="zone-txt">INV-04</text>

                <!-- Substation Dock -->
                <circle cx="100" cy="0" r="5" fill="#f59e0b" />
                <text x="92" y="14" class="home-txt">HOME DOCK</text>

                <!-- Lawnmower Waypoint Path Line -->
                <polyline 
                  :points="flightPathPoints" 
                  fill="none" 
                  stroke="rgba(255, 255, 255, 0.15)" 
                  stroke-width="1.2" 
                  stroke-dasharray="3,3"
                />

                <!-- Waypoint Dots -->
                <g v-for="(wp, idx) in waypoints" :key="wp.id">
                  <circle 
                    :cx="wp.x" 
                    :cy="wp.y" 
                    r="2.5" 
                    :fill="idx < currentWpIdx ? '#10b981' : (idx === currentWpIdx ? '#06b6d4' : '#64748b')" 
                  />
                </g>

                <!-- Live Drone Position Marker -->
                <g :transform="`translate(${droneX}, ${droneY}) rotate(${droneHeading})`">
                  <polygon points="0,-7 5,5 0,2 -5,5" fill="#06b6d4" />
                  <circle cx="0" cy="0" r="8" fill="none" stroke="#06b6d4" stroke-width="1" class="drone-pulse" />
                </g>
              </svg>
            </div>
          </div>

          <!-- Defect Catalog / Report Pane -->
          <div class="defects-card">
            <div class="card-inner-header">
              <span class="card-inner-title">CATALOGED THERMAL DEFECTS (IEC 62446-3)</span>
              <span class="card-inner-sub">{{ catalogedDefects.length }} Anomalies</span>
            </div>

            <div v-if="catalogedDefects.length === 0" class="empty-defects">
              No thermal defects detected. Array operating within normal temperature limits.
            </div>

            <div v-else class="defects-list">
              <div v-for="(d, idx) in catalogedDefects" :key="idx" class="defect-row">
                <div class="d-header">
                  <span class="d-target mono-val">{{ d.target }}</span>
                  <span class="d-class-badge" :class="d.severity === 'CLASS_3' ? 'badge-rose' : 'badge-amber'">
                    {{ d.severity }}
                  </span>
                </div>
                <div class="d-details">
                  <span class="d-type">{{ d.type }}</span>
                  <span class="d-temp mono-val text-rose">{{ d.spot_temp_c }}°C (ΔT: {{ d.delta_t_c > 0 ? '+' : '' }}{{ d.delta_t_c }}°C)</span>
                </div>
                <div class="d-recom">{{ d.recommendation }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  telemetry: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

const isActing = ref(false)
const showReport = ref(false)

const droneData = computed(() => props.telemetry?.drone_inspection || {})
const droneState = computed(() => droneData.value?.state || 'DOCKED')
const droneX = computed(() => droneData.value?.position?.x_m ?? 100.0)
const droneY = computed(() => droneData.value?.position?.y_m ?? 0.0)
const droneHeading = computed(() => droneData.value?.heading_deg ?? 270.0)
const batteryPct = computed(() => droneData.value?.battery_pct ?? 98.0)
const missionProgress = computed(() => droneData.value?.mission_progress_pct ?? 0.0)
const currentWp = computed(() => droneData.value?.current_waypoint || 'WP-01')
const waypoints = computed(() => droneData.value?.waypoints || [])

const flirCamera = computed(() => droneData.value?.flir_camera || {})
const spotTemp = computed(() => flirCamera.value?.spot_temp_c ?? 49.0)
const ambientTemp = computed(() => flirCamera.value?.ambient_temp_c ?? 24.5)
const defectsInView = computed(() => flirCamera.value?.defects_in_view || [])
const catalogedDefects = computed(() => droneData.value?.cataloged_defects || [])
const defectsCount = computed(() => catalogedDefects.value.length)

const currentWpIdx = computed(() => {
  const wp = currentWp.value
  const idx = waypoints.value.findIndex(w => w.id === wp)
  return idx >= 0 ? idx : 0
})

const stateBadgeClass = computed(() => {
  if (droneState.value === 'INSPECTING') return 'badge-emerald'
  if (droneState.value === 'TAKEOFF' || droneState.value === 'RTH') return 'badge-amber'
  return 'badge-slate'
})

const flightPathPoints = computed(() => {
  if (waypoints.value.length === 0) return '100,0'
  const pts = ['100,0', ...waypoints.value.map(w => `${w.x},${w.y}`), '100,0']
  return pts.join(' ')
})

async function launchMission() {
  isActing.value = true
  try {
    await fetch('/api/drone/launch', { method: 'POST' })
  } catch (err) {
    console.error('Failed to launch drone mission:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 1000)
  }
}

async function returnHome() {
  isActing.value = true
  try {
    await fetch('/api/drone/rth', { method: 'POST' })
  } catch (err) {
    console.error('Failed to command drone RTH:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 1000)
  }
}

function close() {
  emit('close')
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(4, 8, 16, 0.88);
  backdrop-filter: blur(10px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
}

.modal-card {
  width: 95vw;
  max-width: 1300px;
  height: 90vh;
  background: #080e1a;
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 30px rgba(245, 158, 11, 0.1);
  overflow: hidden;
}

.modal-header {
  height: 64px;
  background: #0b1324;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.25rem;
  flex-shrink: 0;
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.modal-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
}

.modal-subtitle {
  font-size: 0.72rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.h-badge {
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
}

.hb-lbl {
  font-size: 0.58rem;
  color: #94a3b8;
  font-weight: 600;
}

.hb-val {
  font-size: 0.82rem;
  font-weight: 700;
}

.badge-emerald { background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.3); color: #10b981; }
.badge-amber { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.3); color: #f59e0b; }
.badge-rose { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }
.badge-slate { background: rgba(100, 116, 139, 0.15); border-color: rgba(100, 116, 139, 0.3); color: #94a3b8; }

.modal-close-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 1.4rem;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

/* Modal Body */
.modal-body {
  flex: 1;
  display: flex;
  padding: 1.25rem;
  gap: 1.25rem;
  overflow: hidden;
}

/* Viewfinder Col */
.viewfinder-col {
  flex: 1.4;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.flir-viewport {
  flex: 1;
  background: #040810;
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.flir-hud-top, .flir-hud-bottom {
  height: 32px;
  background: rgba(11, 19, 36, 0.85);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.85rem;
  font-size: 0.65rem;
  color: #94a3b8;
  font-family: 'JetBrains Mono', monospace;
  z-index: 10;
}

.flir-rec {
  color: #64748b;
  font-weight: 700;
}

.flir-rec.active {
  color: #ef4444;
  animation: blinkRec 1s infinite;
}

@keyframes blinkRec {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Thermal Ironbow Screen */
.thermal-screen {
  flex: 1;
  position: relative;
  background: radial-gradient(circle at 50% 50%, #7b1fa2 0%, #d81b60 30%, #f4511e 60%, #ffb300 85%, #000 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* Crosshairs */
.crosshair-wrap {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}

.crosshair-ch {
  width: 40px;
  height: 40px;
  border: 1.5px solid rgba(255, 255, 255, 0.85);
  border-radius: 50%;
  position: relative;
}

.crosshair-ch::before, .crosshair-ch::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.85);
}

.crosshair-ch::before {
  top: 19px;
  left: -8px;
  width: 56px;
  height: 1.5px;
}

.crosshair-ch::after {
  left: 19px;
  top: -8px;
  width: 1.5px;
  height: 56px;
}

.spot-temp-pill {
  margin-top: 10px;
  font-size: 0.85rem;
  font-weight: 800;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
}

.pill-norm { background: rgba(0, 0, 0, 0.75); color: #fff; border: 1px solid rgba(255, 255, 255, 0.3); }
.pill-hot { background: rgba(239, 68, 68, 0.85); color: #fff; border: 1px solid #ef4444; }

/* Bounding box */
.defect-bbox {
  position: absolute;
  border: 2px solid #ef4444;
  background: rgba(239, 68, 68, 0.15);
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
}

.bbox-label {
  position: absolute;
  bottom: 100%;
  left: 0;
  background: #ef4444;
  color: #fff;
  font-size: 0.62rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 2px 2px 0 0;
  white-space: nowrap;
  display: flex;
  gap: 0.4rem;
}

/* Temperature Scale Bar */
.flir-temp-scale {
  position: absolute;
  right: 12px;
  top: 16px;
  bottom: 16px;
  width: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
}

.scale-bar {
  width: 8px;
  flex: 1;
  margin: 4px 0;
  border-radius: 4px;
  background: linear-gradient(to top, #000, #7b1fa2, #d81b60, #f4511e, #ffb300, #fff);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.scale-stop {
  font-size: 0.58rem;
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}

/* Mission Actions */
.mission-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-m {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.btn-launch {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.4);
  color: #f59e0b;
}

.btn-launch:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.25);
  box-shadow: 0 0 15px rgba(245, 158, 11, 0.3);
  color: #fff;
}

.btn-rth {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.btn-rth:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
}

.btn-report {
  background: rgba(6, 182, 212, 0.15);
  border-color: rgba(6, 182, 212, 0.35);
  color: #06b6d4;
}

.btn-report:hover {
  background: rgba(6, 182, 212, 0.25);
  color: #fff;
}

.btn-m:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Right Flight Col */
.flight-col {
  flex: 1.6;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.flight-radar-card, .defects-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 0.85rem;
}

.card-inner-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
}

.card-inner-title {
  font-size: 0.72rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
}

.card-inner-sub {
  font-size: 0.68rem;
}

.radar-svg-wrap {
  width: 100%;
  height: 200px;
  background: rgba(11, 19, 36, 0.6);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flight-svg {
  width: 100%;
  height: 100%;
}

.zone-txt {
  fill: #06b6d4;
  font-size: 8px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.home-txt {
  fill: #f59e0b;
  font-size: 7px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.drone-pulse {
  animation: pulseDrone 1.5s infinite ease-out;
}

@keyframes pulseDrone {
  0% { r: 6; opacity: 1; }
  100% { r: 18; opacity: 0; }
}

/* Defects Card */
.defects-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.empty-defects {
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  padding: 1.5rem 0;
}

.defects-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.defect-row {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-left: 3px solid #ef4444;
  border-radius: 4px;
  padding: 0.5rem 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.d-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.d-target {
  font-size: 0.75rem;
  font-weight: 700;
  color: #f1f5f9;
}

.d-class-badge {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

.d-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
}

.d-type { color: #94a3b8; }

.d-recom {
  font-size: 0.65rem;
  color: #64748b;
}

@media (max-width: 1024px) {
  .modal-body {
    flex-direction: column;
  }
}
</style>
