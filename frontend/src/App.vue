<template>
  <div class="scada-root">
    <!-- Top SCADA Industrial Header -->
    <header class="scada-header">
      <div class="header-brand">
        <div class="brand-logo">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="text-emerald"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </div>
        <div>
          <div class="brand-title">
            GRIDFLOW <span class="brand-sub">// RENEWABLE YIELD FORECASTER</span>
          </div>
          <div class="brand-location">
            PLANT-SOLARIA-01 • Mojave High-Desert Microgrid (25.0 MW)
          </div>
        </div>
      </div>

      <!-- Quick Metrics Strip -->
      <div class="header-metrics-strip">
        <div class="h-metric">
          <span class="h-label">NET INJECTED</span>
          <span class="h-val mono-val text-emerald">{{ Math.round(injectedKw).toLocaleString() }} <small>kW</small></span>
        </div>
        <div class="h-metric">
          <span class="h-label">15M FORECAST</span>
          <span class="h-val mono-val text-cyan">{{ Math.round(forecastKw).toLocaleString() }} <small>kW</small></span>
        </div>
        <div class="h-metric">
          <span class="h-label">P90 SAFE BID</span>
          <span class="h-val mono-val text-cyan">{{ Math.round(p90Kw).toLocaleString() }} <small>kW</small></span>
        </div>
        <div class="h-metric">
          <span class="h-label">SCHEDULE</span>
          <span class="h-val mono-val text-amber">{{ Math.round(scheduleKw).toLocaleString() }} <small>kW</small></span>
        </div>
        <div class="h-metric">
          <span class="h-label">IRRADIANCE</span>
          <span class="h-val mono-val">{{ Math.round(irradiance).toLocaleString() }} <small>W/m²</small></span>
        </div>
        <div class="h-metric">
          <span class="h-label">WIND SPEED</span>
          <span class="h-val mono-val">{{ windSpeed.toFixed(1) }} <small>m/s</small></span>
        </div>
        <div class="h-metric">
          <span class="h-label">BESS SOC</span>
          <span class="h-val mono-val" :class="socPct < 20 ? 'text-rose' : 'text-cyan'">{{ Math.round(socPct) }}%</span>
        </div>
      </div>

      <!-- Connection Status -->
      <div class="header-status">
        <span class="badge" :class="wsConnected ? 'badge-emerald' : 'badge-amber'">
          <span class="status-dot" :class="{ active: wsConnected }"></span>
          {{ wsConnected ? 'MQTT/Kafka 2s Live' : 'Polling Fallback' }}
        </span>
      </div>
    </header>

    <!-- Main SCADA Dashboard Content -->
    <main class="scada-main">
      <!-- Row 1: Geospatial Topology & 15-Minute ML Power Curve -->
      <section class="scada-row row-top">
        <div class="col-half">
          <PlantMap :telemetry="telemetry" />
        </div>
        <div class="col-half">
          <ForecastCurve :history="telemetryHistory" :latest="telemetry" />
        </div>
      </section>

      <!-- Row 2: BESS Storage Dispatch & 32 String Divergence Matrix -->
      <section class="scada-row row-mid">
        <div class="col-mid-left">
          <BessPowerFlow :telemetry="telemetry" />
        </div>
        <div class="col-mid-right">
          <StringMonitor :telemetry="telemetry" />
        </div>
      </section>

      <!-- Row 3: Economic Arbitrage + Alerts + Disturbance Simulator -->
      <section class="scada-row row-bot">
        <div class="col-third">
          <TariffArbitrage :telemetry="telemetry" />
        </div>
        <div class="col-third">
          <AlertFeed :alerts="telemetry.active_alerts || []" @acknowledge="handleAcknowledge" />
        </div>
        <div class="col-third">
          <ScenarioControl @trigger-disturbance="fetchLive" @reset-disturbances="fetchLive" />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import PlantMap from './components/PlantMap.vue'
import ForecastCurve from './components/ForecastCurve.vue'
import BessPowerFlow from './components/BessPowerFlow.vue'
import StringMonitor from './components/StringMonitor.vue'
import TariffArbitrage from './components/TariffArbitrage.vue'
import AlertFeed from './components/AlertFeed.vue'
import ScenarioControl from './components/ScenarioControl.vue'

const telemetry = ref({})
const telemetryHistory = ref([])
const wsConnected = ref(false)
let ws = null
let pollTimer = null

const injectedKw = computed(() => telemetry.value?.bess_dispatch?.final_injected_kw || telemetry.value?.total_renewable_kw || 0)
const forecastKw = computed(() => telemetry.value?.forecast_15m?.predicted_total_kw || 0)
const p90Kw = computed(() => telemetry.value?.forecast_15m?.p90_conservative_kw || 0)
const scheduleKw = computed(() => telemetry.value?.committed_schedule_kw || 0)
const irradiance = computed(() => telemetry.value?.weather?.irradiance_wm2 || 0)
const windSpeed = computed(() => telemetry.value?.weather?.wind_speed_ms || 0)
const socPct = computed(() => telemetry.value?.bess_soc_pct || 65)

onMounted(async () => {
  await fetchHistory()
  await fetchLive()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
  if (pollTimer) clearInterval(pollTimer)
})

async function fetchLive() {
  try {
    const res = await fetch('/api/telemetry/live')
    const data = await res.json()
    telemetry.value = data
    if (!telemetryHistory.value.length) {
      telemetryHistory.value.push(data)
    }
  } catch (err) {
    console.error('Error fetching live telemetry:', err)
  }
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/telemetry/history?limit=40')
    const data = await res.json()
    telemetryHistory.value = data
  } catch (err) {
    console.error('Error fetching history:', err)
  }
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/stream`

  try {
    ws = new WebSocket(wsUrl)
    ws.onopen = () => {
      wsConnected.value = true
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    }
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        telemetry.value = data
        telemetryHistory.value.push(data)
        if (telemetryHistory.value.length > 50) {
          telemetryHistory.value.shift()
        }
      } catch (err) {
        console.error('WS parse error:', err)
      }
    }
    ws.onclose = () => {
      wsConnected.value = false
      startPolling()
    }
    ws.onerror = () => {
      wsConnected.value = false
      startPolling()
    }
  } catch {
    startPolling()
  }
}

function startPolling() {
  if (!pollTimer) {
    pollTimer = setInterval(fetchLive, 2000)
  }
}

async function handleAcknowledge(alert) {
  try {
    await fetch('/api/alerts/acknowledge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        alert_type: alert.alert_type,
        inverter_id: alert.inverter_id,
        string_id: alert.string_id
      })
    })
    fetchLive()
  } catch (err) {
    console.error('Error acknowledging alert:', err)
  }
}
</script>

<style scoped>
.scada-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
  background-image: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.05) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(6, 182, 212, 0.04) 0%, transparent 40%);
}

.scada-header {
  height: 64px;
  background: rgba(13, 17, 26, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 2000;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--glow-emerald);
}

.brand-title {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--text-primary);
}
.brand-sub {
  color: var(--accent-cyan);
  font-weight: 500;
}

.brand-location {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.header-metrics-strip {
  display: flex;
  align-items: center;
  gap: 20px;
}

.h-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.h-label {
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.06em;
}

.h-val {
  font-size: 0.95rem;
  font-weight: 700;
}
.h-val small {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-weight: 400;
}

.text-emerald { color: var(--accent-emerald); }
.text-cyan { color: var(--accent-cyan); }
.text-amber { color: var(--accent-amber); }
.text-rose { color: var(--accent-rose); }

.scada-main {
  flex: 1;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.scada-row {
  display: flex;
  gap: 20px;
}

.col-half {
  flex: 1;
  min-width: 0;
}

.col-mid-left {
  flex: 1;
  min-width: 0;
}

.col-mid-right {
  flex: 1.4;
  min-width: 0;
}

.col-third {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1280px) {
  .header-metrics-strip {
    display: none;
  }
  .scada-row {
    flex-direction: column;
  }
}
</style>
