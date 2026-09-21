<template>
  <div class="sky-radar-card">
    <div class="radar-header">
      <div class="radar-title-wrap">
        <div class="radar-icon-wrap">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
        </div>
        <div>
          <div class="card-title">
            ALL-SKY CAMERA <span class="text-cyan">// CLOUD OPTICAL FLOW & RAMP-RATE RADAR</span>
          </div>
          <div class="card-subtitle">
            Ground-Based Fisheye Imager • 180° Sky Dome • Cloud Base: {{ cloudBaseHeight }}m
          </div>
        </div>
      </div>

      <!-- Quick Status Badges -->
      <div class="radar-header-badges">
        <div class="r-badge" :class="riskBadgeClass">
          <span class="rb-label">RAMP RISK</span>
          <span class="rb-val">{{ rampRiskText }}</span>
        </div>
        <div class="r-badge" :class="bessPrimedClass">
          <span class="rb-label">BESS FAST-RAMP</span>
          <span class="rb-val">{{ isBessPrimed ? 'PRIMED (ACTIVE)' : 'STANDBY' }}</span>
        </div>
      </div>
    </div>

    <!-- Main Content: Radar Scope + Diagnostics Pane -->
    <div class="radar-body">
      <!-- Left: Fisheye Sky Polar Scope -->
      <div class="scope-container">
        <svg class="sky-polar-svg" viewBox="-130 -130 260 260">
          <defs>
            <!-- Radial gradient for sky dome -->
            <radialGradient id="skyGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#0b1a30" />
              <stop offset="70%" stop-color="#07101e" />
              <stop offset="100%" stop-color="#040810" />
            </radialGradient>
            <!-- Cloud glow filter -->
            <filter id="cloudGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <!-- Sun glow filter -->
            <filter id="sunGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          <!-- Sky Dome Background -->
          <circle cx="0" cy="0" r="115" fill="url(#skyGrad)" stroke="rgba(6, 182, 212, 0.3)" stroke-width="1.5" />

          <!-- Concentric Elevation Rings -->
          <!-- 60 deg elevation ring (radius = 115 * 30/90 = 38.3) -->
          <circle cx="0" cy="0" r="38.3" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1" stroke-dasharray="3,3" />
          <text x="2" y="-40" class="ring-label">60°</text>

          <!-- 30 deg elevation ring (radius = 115 * 60/90 = 76.7) -->
          <circle cx="0" cy="0" r="76.7" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1" stroke-dasharray="3,3" />
          <text x="2" y="-78" class="ring-label">30°</text>

          <!-- 0 deg Horizon (radius = 115) -->
          <circle cx="0" cy="0" r="115" fill="none" stroke="rgba(6, 182, 212, 0.2)" stroke-width="1" />
          <text x="2" y="-117" class="ring-label">0° Horizon</text>

          <!-- Crosshairs (Zenith at center) -->
          <line x1="-115" y1="0" x2="115" y2="0" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1" />
          <line x1="0" y1="-115" x2="0" y2="115" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1" />
          <circle cx="0" cy="0" r="2.5" fill="#06b6d4" />

          <!-- Cardinal Labels -->
          <text x="0" y="-103" text-anchor="middle" class="cardinal-label text-cyan">N</text>
          <text x="0" y="110" text-anchor="middle" class="cardinal-label">S</text>
          <text x="106" y="4" text-anchor="middle" class="cardinal-label">E</text>
          <text x="-106" y="4" text-anchor="middle" class="cardinal-label">W</text>

          <!-- Ground Solar Array Perimeter footprint at center -->
          <rect x="-14" y="-14" width="28" height="28" fill="rgba(16, 185, 129, 0.12)" stroke="#10b981" stroke-width="0.8" rx="2" />
          <text x="0" y="2" text-anchor="middle" class="array-tag">PLANT</text>

          <!-- Ground Shadow Projection Footprint -->
          <g v-if="shadowDist < 1200" :transform="`translate(${shadowPos.x}, ${shadowPos.y})`">
            <ellipse 
              cx="0" 
              cy="0" 
              :rx="shadowRadius" 
              :ry="shadowRadius * 0.85" 
              fill="rgba(239, 68, 68, 0.25)" 
              stroke="#ef4444" 
              stroke-width="1.2" 
              stroke-dasharray="4,2"
              class="shadow-pulse"
            />
            <text x="0" y="3" text-anchor="middle" class="shadow-label">SHADOW</text>
          </g>

          <!-- Animated Clouds with Optical Flow Vectors -->
          <g v-for="(cloud, idx) in skyClouds" :key="idx" :transform="`translate(${cloud.x}, ${cloud.y})`">
            <!-- Cloud Body -->
            <circle 
              cx="0" 
              cy="0" 
              :r="cloud.r" 
              fill="rgba(226, 232, 240, 0.35)" 
              stroke="rgba(255, 255, 255, 0.7)" 
              stroke-width="1"
              filter="url(#cloudGlow)" 
            />
            <circle cx="0" cy="0" :r="cloud.r * 0.5" fill="rgba(255, 255, 255, 0.45)" />

            <!-- Optical Flow Velocity Arrow (u, v) -->
            <line 
              x1="0" 
              y1="0" 
              :x2="cloud.vx * 30" 
              :y2="cloud.vy * 30" 
              stroke="#06b6d4" 
              stroke-width="2" 
              stroke-linecap="round"
            />
            <circle :cx="cloud.vx * 30" :cy="cloud.vy * 30" r="2" fill="#06b6d4" />
          </g>

          <!-- Sun Position Indicator Marker -->
          <g :transform="`translate(${sunPos.x}, ${sunPos.y})`" filter="url(#sunGlow)">
            <circle cx="0" cy="0" r="7" fill="#f59e0b" />
            <circle cx="0" cy="0" r="3" fill="#fff" />
            <text x="10" y="4" class="sun-tag">SUN ({{ sunElevation.toFixed(0) }}°)</text>
          </g>
        </svg>

        <!-- Polar Scope Legend Overlay -->
        <div class="scope-overlay-tag">
          <span>CMV OPTICAL FLOW</span>
          <span class="mono-val text-cyan">{{ cloudSpeed }} m/s @ {{ cloudHeading }}°</span>
        </div>
      </div>

      <!-- Right: Ramp-Rate & BESS Fast-Ramp Diagnostics Pane -->
      <div class="diagnostics-pane">
        <!-- Time-to-Impact Big Digital Readout -->
        <div class="tti-card" :class="{ 'tti-alert': isImminentImpact }">
          <div class="tti-header">
            <span class="tti-title">TIME TO SHADOW IMPACT</span>
            <span v-if="isImminentImpact" class="tti-live-pulse">⚠️ IMMINENT</span>
          </div>
          <div class="tti-display mono-val">
            {{ formattedTti }}
          </div>
          <div class="tti-sub">
            Distance to array: <span class="text-white">{{ Math.round(shadowDist) }} m</span> • Speed: <span class="text-white">{{ cloudSpeed }} m/s</span>
          </div>
        </div>

        <!-- Predicted Ramp Meter vs Grid Interconnection Limit -->
        <div class="ramp-meter-card">
          <div class="meter-header">
            <span class="meter-title">PREDICTED SOLAR RAMP-RATE</span>
            <span class="mono-val text-bold" :class="predictedRamp < -2.0 ? 'text-rose' : 'text-emerald'">
              {{ predictedRamp.toFixed(2) }} <small>MW/min</small>
            </span>
          </div>
          <!-- Gauge Bar -->
          <div class="meter-bar-track">
            <!-- Normal limit marker at -2.0 MW/min -->
            <div class="meter-limit-line" style="left: 33.3%;"></div>
            <div 
              class="meter-fill" 
              :style="{ width: `${rampMeterWidth}%`, background: rampMeterColor }"
            ></div>
          </div>
          <div class="meter-legend">
            <span class="text-rose">-6.0 MW/min (Severe)</span>
            <span class="limit-label">Limit: -2.0 MW/min</span>
            <span class="text-emerald">0.0 (Stable)</span>
          </div>
        </div>

        <!-- BESS Fast-Ramp Buffer Status & Readiness -->
        <div class="bess-buffer-card" :class="{ 'buffer-active': isBessPrimed }">
          <div class="buffer-header">
            <div class="b-status-icon">
              <span class="buffer-indicator" :class="{ primed: isBessPrimed }"></span>
            </div>
            <div>
              <div class="buffer-title">BESS FAST-RAMP BUFFER</div>
              <div class="buffer-sub">Automated Ramp-Rate Mitigation Subroutine</div>
            </div>
            <span class="buffer-badge" :class="isBessPrimed ? 'badge-primed' : 'badge-standby'">
              {{ isBessPrimed ? 'BUFFER PRIMED' : 'STANDBY' }}
            </span>
          </div>
          <div class="buffer-stats">
            <div class="b-stat">
              <span class="b-lbl">PRE-DISPATCH READY</span>
              <span class="b-val mono-val text-cyan">{{ isBessPrimed ? '+4,800' : '0' }} <small>kW</small></span>
            </div>
            <div class="b-stat">
              <span class="b-lbl">SMOOTHED NET RAMP</span>
              <span class="b-val mono-val text-emerald">&lt; 0.45 <small>MW/min</small></span>
            </div>
            <div class="b-stat">
              <span class="b-lbl">AVOIDED PENALTY</span>
              <span class="b-val mono-val text-amber">$1,850 <small>/ event</small></span>
            </div>
          </div>
        </div>

        <!-- Trigger Approaching Cloud Simulation Button -->
        <div class="radar-action-wrap">
          <button @click="triggerCloudApproach" class="btn-cloud-trigger" :disabled="isSimulating">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/><polygon points="12 2 15 8 9 8 12 2"/></svg>
            {{ isSimulating ? 'Simulating Cloud Transit...' : 'Simulate Approaching Cumulus Cloud' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  telemetry: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['cloud-triggered'])
const isSimulating = ref(false)

const cloudTracking = computed(() => props.telemetry?.cloud_tracking || {})
const spatialTracking = computed(() => props.telemetry?.spatial_tracking || {})

const cloudBaseHeight = computed(() => cloudTracking.value?.cloud_base_height_m || 1200)
const cloudSpeed = computed(() => (cloudTracking.value?.cloud_speed_ms || 14.8).toFixed(1))
const cloudHeading = computed(() => (cloudTracking.value?.cloud_heading_deg || 245.0).toFixed(0))
const ttiSec = computed(() => cloudTracking.value?.time_to_impact_sec ?? 999.0)
const predictedRamp = computed(() => cloudTracking.value?.predicted_ramp_mw_min ?? 0.0)
const rampRisk = computed(() => cloudTracking.value?.ramp_violation_risk || 'NORMAL')
const isBessPrimed = computed(() => Boolean(cloudTracking.value?.bess_fast_ramp_primed))

const sunElevation = computed(() => spatialTracking.value?.sun_elevation_deg ?? 48.0)
const sunAzimuth = computed(() => spatialTracking.value?.sun_azimuth_deg ?? 194.0)

const isImminentImpact = computed(() => ttiSec.value < 90.0 && ttiSec.value > 0.0)

const formattedTti = computed(() => {
  if (ttiSec.value >= 999.0) return '-- : --'
  const total = Math.max(0, Math.floor(ttiSec.value))
  const mins = Math.floor(total / 60)
  const secs = total % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

const shadowDist = computed(() => cloudTracking.value?.ground_shadow?.dist_to_center_m || 1500)
const shadowRadius = computed(() => Math.min(35, Math.max(12, (cloudTracking.value?.ground_shadow?.radius_m || 600) / 40)))

// Polar projections for SVG scope
// Center is (0, 0), radius is 115 px (representing 90 deg zenith distance)
const sunPos = computed(() => {
  const elev = Math.max(0.0, Math.min(90.0, sunElevation.value))
  const zenithDist = (90.0 - elev) / 90.0 * 115.0 // 0 at zenith, 115 at horizon
  const azimRad = (sunAzimuth.value - 90.0) * (Math.PI / 180.0) // 0 deg is East in standard Cartesian, -90 for North
  return {
    x: zenithDist * Math.cos(azimRad),
    y: zenithDist * Math.sin(azimRad)
  }
})

const shadowPos = computed(() => {
  const gx = cloudTracking.value?.ground_shadow?.x_m || 800
  const gy = cloudTracking.value?.ground_shadow?.y_m || 600
  // Scale 2000m to 110px
  const scale = 110.0 / 1800.0
  return {
    x: Math.max(-115, Math.min(115, gx * scale)),
    y: Math.max(-115, Math.min(115, -gy * scale))
  }
})

const skyClouds = computed(() => {
  const rawClouds = cloudTracking.value?.sky_clouds || []
  return rawClouds.map(c => {
    const rDist = c.r * 115.0
    const angleRad = (c.angle_deg - 90.0) * (Math.PI / 180.0)
    return {
      x: rDist * Math.cos(angleRad),
      y: rDist * Math.sin(angleRad),
      r: Math.max(8, c.radius_norm * 115.0),
      vx: c.vx_norm,
      vy: c.vy_norm
    }
  })
})

const rampRiskText = computed(() => {
  if (rampRisk.value === 'CRITICAL_RAMP_DOWN') return 'CRITICAL RAMP'
  if (rampRisk.value === 'WARNING_RAMP_DOWN') return 'RAMP WARNING'
  return 'NORMAL'
})

const riskBadgeClass = computed(() => {
  if (rampRisk.value === 'CRITICAL_RAMP_DOWN') return 'badge-rose'
  if (rampRisk.value === 'WARNING_RAMP_DOWN') return 'badge-amber'
  return 'badge-emerald'
})

const bessPrimedClass = computed(() => {
  return isBessPrimed.value ? 'badge-cyan' : 'badge-slate'
})

const rampMeterWidth = computed(() => {
  // Ramp from 0 to -6 MW/min maps to 100% to 0%
  const clamped = Math.max(-6.0, Math.min(0.0, predictedRamp.value))
  return (1.0 - (Math.abs(clamped) / 6.0)) * 100.0
})

const rampMeterColor = computed(() => {
  if (predictedRamp.value <= -3.5) return '#ef4444'
  if (predictedRamp.value <= -2.0) return '#f59e0b'
  return '#10b981'
})

async function triggerCloudApproach() {
  isSimulating.value = true
  try {
    await fetch('/api/scenarios/inject/cloud_cover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duration_sec: 45, drop_pct: 75.0 })
    })
    emit('cloud-triggered')
  } catch (err) {
    console.error('Error triggering cloud scenario:', err)
  } finally {
    setTimeout(() => {
      isSimulating.value = false
    }, 4000)
  }
}
</script>

<style scoped>
.sky-radar-card {
  background: var(--bg-card, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.radar-header {
  padding: 0.85rem 1.15rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.7);
}

.radar-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.radar-icon-wrap {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.03em;
}

.card-subtitle {
  font-size: 0.7rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.radar-header-badges {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.r-badge {
  display: flex;
  flex-direction: column;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  border: 1px solid transparent;
}

.rb-label {
  font-size: 0.58rem;
  color: #94a3b8;
}

.badge-rose { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }
.badge-amber { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.3); color: #f59e0b; }
.badge-emerald { background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.3); color: #10b981; }
.badge-cyan { background: rgba(6, 182, 212, 0.15); border-color: rgba(6, 182, 212, 0.3); color: #06b6d4; }
.badge-slate { background: rgba(100, 116, 139, 0.15); border-color: rgba(100, 116, 139, 0.3); color: #94a3b8; }

/* Body */
.radar-body {
  display: flex;
  padding: 1rem;
  gap: 1.25rem;
}

/* Left: Polar Scope */
.scope-container {
  position: relative;
  width: 260px;
  height: 260px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sky-polar-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.ring-label {
  fill: #64748b;
  font-size: 7px;
  font-family: 'JetBrains Mono', monospace;
}

.cardinal-label {
  fill: #94a3b8;
  font-size: 9px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.array-tag {
  fill: #10b981;
  font-size: 5px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.sun-tag {
  fill: #f59e0b;
  font-size: 7px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.shadow-label {
  fill: #ef4444;
  font-size: 6px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.shadow-pulse {
  animation: pulseShadow 2s infinite ease-in-out;
}

@keyframes pulseShadow {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 0.3; }
}

.scope-overlay-tag {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(11, 19, 36, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 0.2rem 0.45rem;
  font-size: 0.62rem;
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

/* Right: Diagnostics Pane */
.diagnostics-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* TTI Card */
.tti-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
  transition: all 0.2s;
}

.tti-alert {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.2);
}

.tti-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tti-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
}

.tti-live-pulse {
  font-size: 0.65rem;
  font-weight: 700;
  color: #ef4444;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.tti-display {
  font-size: 1.6rem;
  font-weight: 800;
  color: #f1f5f9;
  line-height: 1.2;
  margin: 0.2rem 0;
}

.tti-sub {
  font-size: 0.68rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

/* Ramp Meter */
.ramp-meter-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
}

.meter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.meter-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: #94a3b8;
}

.meter-bar-track {
  position: relative;
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease, background 0.4s ease;
}

.meter-limit-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ef4444;
  z-index: 2;
}

.meter-legend {
  display: flex;
  justify-content: space-between;
  font-size: 0.62rem;
  font-family: 'JetBrains Mono', monospace;
  margin-top: 0.25rem;
  color: #64748b;
}

.limit-label {
  color: #f59e0b;
  font-weight: 600;
}

/* BESS Buffer Card */
.bess-buffer-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
  transition: all 0.2s;
}

.buffer-active {
  background: rgba(6, 182, 212, 0.06);
  border-color: rgba(6, 182, 212, 0.35);
}

.buffer-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
}

.buffer-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
}

.buffer-indicator.primed {
  background: #06b6d4;
  box-shadow: 0 0 10px #06b6d4;
}

.buffer-title {
  font-size: 0.72rem;
  font-weight: 700;
  color: #f1f5f9;
}

.buffer-sub {
  font-size: 0.62rem;
  color: #64748b;
}

.buffer-badge {
  margin-left: auto;
  font-size: 0.62rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.badge-primed {
  background: rgba(6, 182, 212, 0.2);
  color: #06b6d4;
  border: 1px solid rgba(6, 182, 212, 0.4);
}

.badge-standby {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

.buffer-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  padding-top: 0.4rem;
}

.b-stat {
  display: flex;
  flex-direction: column;
}

.b-lbl {
  font-size: 0.58rem;
  color: #64748b;
}

.b-val {
  font-size: 0.8rem;
  font-weight: 700;
}

/* Action Button */
.radar-action-wrap {
  margin-top: auto;
}

.btn-cloud-trigger {
  width: 100%;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.3);
  color: #06b6d4;
  padding: 0.45rem 0.8rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.btn-cloud-trigger:hover:not(:disabled) {
  background: rgba(6, 182, 212, 0.2);
  border-color: rgba(6, 182, 212, 0.6);
  color: #fff;
  box-shadow: 0 0 12px rgba(6, 182, 212, 0.2);
}

.btn-cloud-trigger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .radar-body {
    flex-direction: column;
    align-items: center;
  }
}
</style>
