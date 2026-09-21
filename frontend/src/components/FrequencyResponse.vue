<template>
  <div class="freq-response-card">
    <!-- Header -->
    <div class="freq-header">
      <div class="freq-title-wrap">
        <div class="freq-icon-wrap">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-emerald"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
        </div>
        <div>
          <div class="card-title">
            FAST FREQUENCY RESPONSE (FFR) <span class="text-emerald">// SYNTHETIC INERTIA & PRIMARY DROOP</span>
          </div>
          <div class="card-subtitle">
            Nominal 60.000 Hz • Deadband ±0.030 Hz • Droop s = 4.0% • Inertia H = 4.5s
          </div>
        </div>
      </div>

      <!-- Frequency Status Badges -->
      <div class="freq-badges">
        <div class="f-badge" :class="statusBadgeClass">
          <span class="fb-lbl">GRID STATUS</span>
          <span class="fb-val">{{ statusText }}</span>
        </div>
        <div class="f-badge badge-slate">
          <span class="fb-lbl">RoCoF</span>
          <span class="fb-val mono-val" :class="rocofVal < -0.1 ? 'text-rose' : 'text-cyan'">{{ rocofVal > 0 ? '+' : '' }}{{ rocofVal.toFixed(3) }} Hz/s</span>
        </div>
        <div class="f-badge" :class="isFfrBurst ? 'badge-rose-pulse' : 'badge-emerald'">
          <span class="fb-lbl">FFR BURST</span>
          <span class="fb-val">{{ isFfrBurst ? 'TRIGGERED (+5 MW)' : 'STANDBY' }}</span>
        </div>
      </div>
    </div>

    <!-- Main Grid: Needle Gauge + Oscilloscope + Ancillary Revenue -->
    <div class="freq-body">
      <!-- 1. Arc Frequency Gauge -->
      <div class="gauge-col">
        <div class="gauge-wrapper">
          <svg class="arc-gauge-svg" viewBox="0 0 220 130">
            <!-- Background track (59.60 Hz to 60.40 Hz = 180 degrees) -->
            <!-- 59.60 to 59.80: Red (Critical Under-frequency FFR) -->
            <path d="M 20 110 A 90 90 0 0 1 65 32" fill="none" stroke="#ef4444" stroke-width="12" stroke-linecap="round" />
            <!-- 59.80 to 59.97: Amber (Under-frequency Droop) -->
            <path d="M 65 32 A 90 90 0 0 1 103 20" fill="none" stroke="#f59e0b" stroke-width="12" />
            <!-- 59.97 to 60.03: Emerald (Deadband Normal) -->
            <path d="M 103 20 A 90 90 0 0 1 117 20" fill="none" stroke="#10b981" stroke-width="14" />
            <!-- 60.03 to 60.20: Amber (Over-frequency Droop) -->
            <path d="M 117 20 A 90 90 0 0 1 155 32" fill="none" stroke="#f59e0b" stroke-width="12" />
            <!-- 60.20 to 60.40: Red (Over-frequency Trip) -->
            <path d="M 155 32 A 90 90 0 0 1 200 110" fill="none" stroke="#ef4444" stroke-width="12" stroke-linecap="round" />

            <!-- Deadband boundary markers -->
            <line x1="103" y1="12" x2="103" y2="28" stroke="#10b981" stroke-width="1.5" />
            <line x1="117" y1="12" x2="117" y2="28" stroke="#10b981" stroke-width="1.5" />

            <!-- Needle Pivot & Needle -->
            <g :transform="`rotate(${needleAngle}, 110, 110)`">
              <polygon points="107,110 110,24 113,110" fill="#f1f5f9" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.8))" />
              <circle cx="110" cy="110" r="7" fill="#0ea5e9" />
              <circle cx="110" cy="110" r="3" fill="#fff" />
            </g>

            <!-- Ticks & Text -->
            <text x="18" y="125" class="gauge-tick">59.60</text>
            <text x="50" y="32" class="gauge-tick">59.80</text>
            <text x="110" y="14" class="gauge-tick-center">60.00</text>
            <text x="170" y="32" class="gauge-tick">60.20</text>
            <text x="202" y="125" class="gauge-tick">60.40</text>
          </svg>

          <!-- Large Frequency Readout -->
          <div class="freq-readout-wrap">
            <span class="freq-big-val mono-val" :class="frequencyColorClass">
              {{ currentFreq.toFixed(3) }}
            </span>
            <span class="freq-unit">Hz</span>
          </div>
          <div class="freq-dev-sub mono-val">
            Δf: <span :class="deltaF < 0 ? 'text-amber' : 'text-cyan'">{{ deltaF > 0 ? '+' : '' }}{{ deltaF.toFixed(3) }} Hz</span>
          </div>
        </div>
      </div>

      <!-- 2. Dual-Trace Oscilloscope (ECharts) -->
      <div class="oscilloscope-col">
        <div class="scope-header">
          <span class="scope-title">SUB-SECOND FREQUENCY TRANSIENT & BESS FCR INJECTION</span>
          <span class="scope-legend">
            <span class="dot-freq"></span> Grid Frequency (Hz)
            <span class="dot-pwr"></span> BESS Response (kW)
          </span>
        </div>
        <div ref="chartEl" class="scope-chart"></div>
      </div>

      <!-- 3. Ancillary Revenue & Disturbance Controls -->
      <div class="market-col">
        <!-- Revenue Card -->
        <div class="ancillary-market-card">
          <div class="m-card-title">ANCILLARY SERVICES SETTLEMENT</div>
          <div class="m-revenue-val mono-val text-emerald">
            ${{ accumulatedRevenue.toFixed(2) }}
          </div>
          <div class="m-revenue-sub">CAISO Regulation Up/Down + Mileage</div>

          <div class="m-breakdown-grid">
            <div class="m-row">
              <span class="m-lbl">Synthetic Inertia (P_iner)</span>
              <span class="m-val mono-val text-cyan">{{ pInertia.toFixed(1) }} kW</span>
            </div>
            <div class="m-row">
              <span class="m-lbl">Primary Droop (P_droop)</span>
              <span class="m-val mono-val text-amber">{{ pDroop.toFixed(1) }} kW</span>
            </div>
            <div class="m-row">
              <span class="m-lbl">FFR Nadir Burst (P_ffr)</span>
              <span class="m-val mono-val text-rose">{{ pFfrBurst.toFixed(1) }} kW</span>
            </div>
            <div class="m-row m-row-total">
              <span class="m-lbl font-bold">Total FCR Injection</span>
              <span class="m-val mono-val font-bold text-emerald">{{ totalFcr.toFixed(1) }} kW</span>
            </div>
          </div>
        </div>

        <!-- Disturbance Injection Controls -->
        <div class="freq-actions-wrap">
          <div class="actions-label">SIMULATE GRID DISTURBANCE</div>
          <div class="actions-btn-group">
            <button @click="triggerGenTrip" class="btn-disturb btn-disturb-trip" :disabled="isActing">
              ⚡ 1.2 GW Gen Trip (59.68 Hz)
            </button>
            <button @click="triggerLoadShed" class="btn-disturb btn-disturb-shed" :disabled="isActing">
              📉 Load Rejection (60.32 Hz)
            </button>
            <button @click="resetGrid" class="btn-disturb btn-disturb-reset" :disabled="isActing">
              ↺ Normal Grid (60.00 Hz)
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  telemetry: {
    type: Object,
    default: () => ({})
  }
})

const chartEl = ref(null)
let chart = null
const isActing = ref(false)

// Historical trace buffers for oscilloscope
const timeLabels = ref([])
const freqHistory = ref([])
const powerHistory = ref([])

const freqData = computed(() => props.telemetry?.frequency_response || {})
const currentFreq = computed(() => freqData.value?.grid_frequency_hz ?? 60.000)
const rocofVal = computed(() => freqData.value?.rocof_hz_s ?? 0.0)
const statusText = computed(() => freqData.value?.frequency_status ?? 'DEADBAND_NORMAL')
const isFfrBurst = computed(() => Boolean(freqData.value?.ffr_active))
const pInertia = computed(() => freqData.value?.p_inertia_kw ?? 0.0)
const pDroop = computed(() => freqData.value?.p_droop_kw ?? 0.0)
const pFfrBurst = computed(() => freqData.value?.p_ffr_burst_kw ?? 0.0)
const totalFcr = computed(() => freqData.value?.total_fcr_kw ?? 0.0)
const accumulatedRevenue = computed(() => freqData.value?.ancillary_revenue_usd ?? 1240.50)

const deltaF = computed(() => currentFreq.value - 60.000)

// Needle angle calculation:
// 59.60 Hz = -90 deg (left), 60.00 Hz = 0 deg (top), 60.40 Hz = +90 deg (right)
const needleAngle = computed(() => {
  const f = Math.max(59.60, Math.min(60.40, currentFreq.value))
  return ((f - 60.00) / 0.40) * 90.0
})

const frequencyColorClass = computed(() => {
  if (currentFreq.value < 59.80 || currentFreq.value > 60.20) return 'text-rose'
  if (currentFreq.value < 59.97 || currentFreq.value > 60.03) return 'text-amber'
  return 'text-emerald'
})

const statusBadgeClass = computed(() => {
  if (statusText.value === 'CRITICAL_FFR_BURST') return 'badge-rose'
  if (statusText.value.includes('UNDER_FREQUENCY') || statusText.value.includes('OVER_FREQUENCY')) return 'badge-amber'
  return 'badge-emerald'
})

function initChart() {
  if (!chartEl.value) return
  chart = echarts.init(chartEl.value)

  // Initialize with last 25 dummy seconds if empty
  const now = new Date()
  for (let i = 25; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 2000)
    timeLabels.value.push(t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    freqHistory.value.push(60.000)
    powerHistory.value.push(0.0)
  }

  renderChart()
  window.addEventListener('resize', handleResize)
}

function renderChart() {
  if (!chart) return

  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '10%',
      right: '12%',
      top: '15%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11, 19, 36, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#f1f5f9', fontSize: 11, fontFamily: 'JetBrains Mono' }
    },
    xAxis: {
      type: 'category',
      data: timeLabels.value,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: '#64748b', fontSize: 9, fontFamily: 'JetBrains Mono' },
      splitLine: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        name: 'Freq (Hz)',
        min: 59.60,
        max: 60.40,
        interval: 0.20,
        position: 'left',
        axisLine: { lineStyle: { color: '#10b981' } },
        axisLabel: { color: '#10b981', fontSize: 9, fontFamily: 'JetBrains Mono' },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } }
      },
      {
        type: 'value',
        name: 'BESS (kW)',
        min: -5000,
        max: 5000,
        interval: 2500,
        position: 'right',
        axisLine: { lineStyle: { color: '#06b6d4' } },
        axisLabel: { color: '#06b6d4', fontSize: 9, fontFamily: 'JetBrains Mono' },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: 'Grid Frequency',
        type: 'line',
        yAxisIndex: 0,
        data: freqHistory.value,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#10b981', width: 2 },
        markLine: {
          symbol: 'none',
          data: [
            { yAxis: 60.00, lineStyle: { color: '#10b981', type: 'solid', width: 1 } },
            { yAxis: 59.97, lineStyle: { color: '#64748b', type: 'dashed', width: 1 } },
            { yAxis: 60.03, lineStyle: { color: '#64748b', type: 'dashed', width: 1 } }
          ]
        }
      },
      {
        name: 'BESS FCR Injection',
        type: 'line',
        yAxisIndex: 1,
        data: powerHistory.value,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#06b6d4', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
            { offset: 1, color: 'rgba(6, 182, 212, 0.0)' }
          ])
        }
      }
    ]
  }

  chart.setOption(option)
}

function handleResize() {
  chart?.resize()
}

// Watch telemetry updates and append to rolling buffer
watch(() => props.telemetry?.timestamp, () => {
  const tStr = new Date(props.telemetry.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  
  timeLabels.value.push(tStr)
  freqHistory.value.push(currentFreq.value)
  powerHistory.value.push(totalFcr.value)

  if (timeLabels.value.length > 25) {
    timeLabels.value.shift()
    freqHistory.value.shift()
    powerHistory.value.shift()
  }

  if (chart) {
    chart.setOption({
      xAxis: { data: timeLabels.value },
      series: [
        { data: freqHistory.value },
        { data: powerHistory.value }
      ]
    })
  }
})

// Trigger handlers
async function triggerGenTrip() {
  isActing.value = true
  try {
    await fetch('/api/frequency/trip-generator', { method: 'POST' })
  } catch (err) {
    console.error('Failed to trigger generator trip:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 2000)
  }
}

async function triggerLoadShed() {
  isActing.value = true
  try {
    await fetch('/api/frequency/load-shed', { method: 'POST' })
  } catch (err) {
    console.error('Failed to trigger load shed:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 2000)
  }
}

async function resetGrid() {
  isActing.value = true
  try {
    await fetch('/api/frequency/reset', { method: 'POST' })
  } catch (err) {
    console.error('Failed to reset grid:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 1000)
  }
}

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.freq-response-card {
  background: var(--bg-card, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.freq-header {
  padding: 0.85rem 1.15rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.7);
}

.freq-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.freq-icon-wrap {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
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

.freq-badges {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.f-badge {
  display: flex;
  flex-direction: column;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  border: 1px solid transparent;
}

.fb-lbl {
  font-size: 0.58rem;
  color: #94a3b8;
}

.badge-rose { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }
.badge-rose-pulse {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.6);
  color: #ef4444;
  animation: pulseFfr 1s infinite;
}
.badge-amber { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.3); color: #f59e0b; }
.badge-emerald { background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.3); color: #10b981; }
.badge-slate { background: rgba(100, 116, 139, 0.15); border-color: rgba(100, 116, 139, 0.3); color: #94a3b8; }

@keyframes pulseFfr {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.7; }
}

/* Body */
.freq-body {
  display: flex;
  padding: 1rem;
  gap: 1.25rem;
}

/* 1. Gauge Col */
.gauge-col {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.gauge-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.arc-gauge-svg {
  width: 220px;
  height: 130px;
  overflow: visible;
}

.gauge-tick {
  fill: #64748b;
  font-size: 8px;
  font-family: 'JetBrains Mono', monospace;
  text-anchor: middle;
}

.gauge-tick-center {
  fill: #10b981;
  font-size: 9px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  text-anchor: middle;
}

.freq-readout-wrap {
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
  margin-top: -10px;
}

.freq-big-val {
  font-size: 1.8rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.freq-unit {
  font-size: 0.85rem;
  font-weight: 700;
  color: #64748b;
}

.freq-dev-sub {
  font-size: 0.72rem;
  color: #64748b;
}

/* 2. Oscilloscope Col */
.oscilloscope-col {
  flex: 1.6;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.scope-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}

.scope-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
}

.scope-legend {
  font-size: 0.65rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dot-freq {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.dot-pwr {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #06b6d4;
}

.scope-chart {
  width: 100%;
  height: 180px;
}

/* 3. Market Col */
.market-col {
  flex: 1.2;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.ancillary-market-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
}

.m-card-title {
  font-size: 0.65rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
}

.m-revenue-val {
  font-size: 1.4rem;
  font-weight: 800;
  line-height: 1.2;
  margin: 0.2rem 0;
}

.m-revenue-sub {
  font-size: 0.65rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.m-breakdown-grid {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  padding-top: 0.4rem;
}

.m-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
}

.m-lbl {
  color: #94a3b8;
}

.m-row-total {
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
  padding-top: 0.25rem;
  margin-top: 0.2rem;
}

/* Disturbance Actions */
.freq-actions-wrap {
  margin-top: auto;
}

.actions-label {
  font-size: 0.62rem;
  font-weight: 700;
  color: #64748b;
  margin-bottom: 0.35rem;
}

.actions-btn-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}

.btn-disturb {
  border-radius: 4px;
  padding: 0.35rem 0.5rem;
  font-size: 0.68rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-disturb-trip {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.btn-disturb-trip:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.25);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}

.btn-disturb-shed {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.btn-disturb-shed:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.25);
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
}

.btn-disturb-reset {
  grid-column: span 2;
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.btn-disturb-reset:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
}

.btn-disturb:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1024px) {
  .freq-body {
    flex-direction: column;
  }
}
</style>
