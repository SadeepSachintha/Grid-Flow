<template>
  <div class="glass-panel bess-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-amber">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber"><rect width="16" height="10" x="2" y="7" rx="2" ry="2"/><line x1="22" x2="22" y1="11" y2="13"/></svg>
        </div>
        <div>
          <h3 class="card-title">BESS Storage & Dispatch Optimization</h3>
          <p class="card-subtitle">10.0 MWh / 5.0 MW C-Rate • Real-Time Schedule Balancing</p>
        </div>
      </div>
      <div class="header-right">
        <span class="badge" :class="dispatchModeClass">
          {{ dispatchModeText }}
        </span>
      </div>
    </div>

    <div class="bess-body">
      <!-- Radial SoC Gauge -->
      <div class="soc-gauge-col">
        <div class="gauge-wrap" ref="gaugeRef"></div>
        <div class="soc-label-center">
          <span class="soc-num mono-val">{{ Math.round(socPct) }}%</span>
          <span class="soc-sub">State of Charge</span>
        </div>
      </div>

      <!-- Power Flow & Economic Balancing Stats -->
      <div class="flow-stats-col">
        <div class="flow-metric-row">
          <div class="metric-item">
            <span class="metric-label">Dispatch Setpoint</span>
            <span class="metric-val mono-val" :class="dispatchKw > 0 ? 'text-amber' : (dispatchKw < 0 ? 'text-cyan' : '')">
              {{ dispatchKw > 0 ? '+' : '' }}{{ dispatchKw.toLocaleString() }} kW
            </span>
            <span class="metric-hint">{{ dispatchKw > 0 ? 'Discharging to Grid' : (dispatchKw < 0 ? 'Charging from Array' : 'Idle') }}</span>
          </div>

          <div class="metric-item">
            <span class="metric-label">Schedule Deviation</span>
            <span class="metric-val mono-val" :class="Math.abs(deviationKw) > 1000 ? 'text-rose' : 'text-emerald'">
              {{ deviationKw > 0 ? '+' : '' }}{{ deviationKw.toLocaleString() }} kW
            </span>
            <span class="metric-hint">Tolerance: ±5%</span>
          </div>
        </div>

        <div class="flow-metric-row">
          <div class="metric-item">
            <span class="metric-label">Avoided Penalties</span>
            <span class="metric-val mono-val text-emerald">
              ${{ Math.round(accumulatedSavings).toLocaleString() }}
            </span>
            <span class="metric-hint">Contractual Non-Compliance Saved</span>
          </div>

          <div class="metric-item">
            <span class="metric-label">Discharge Headroom</span>
            <span class="metric-val mono-val">{{ Math.round(maxDischargeKw).toLocaleString() }} kW</span>
            <span class="metric-hint">Max Instantaneous Injection</span>
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

const gaugeRef = ref(null)
let gaugeChart = null

const bessData = computed(() => props.telemetry?.bess_dispatch || {})
const socPct = computed(() => props.telemetry?.bess_soc_pct || 65.0)
const dispatchKw = computed(() => bessData.value.battery_dispatch_kw || 0.0)
const deviationKw = computed(() => bessData.value.deviation_kw || 0.0)
const maxDischargeKw = computed(() => bessData.value.available_discharge_kw || 5000.0)
const accumulatedSavings = computed(() => props.telemetry?.financial_kpis?.total_savings_usd || 0.0)

const dispatchModeText = computed(() => {
  const mode = bessData.value.dispatch_mode || 'STANDBY'
  if (mode === 'DISCHARGING_DEFICIT_COMPENSATION') return 'Discharging (Deficit)'
  if (mode === 'CHARGING_SURPLUS_ABSORPTION') return 'Charging (Surplus)'
  if (mode === 'PEAK_TARIFF_ARBITRAGE') return 'Peak Arbitrage'
  if (mode === 'OFF_PEAK_CHARGING') return 'Off-Peak Charging'
  return 'Standby / Balanced'
})

const dispatchModeClass = computed(() => {
  const mode = bessData.value.dispatch_mode || 'STANDBY'
  if (mode.includes('DISCHARGING') || mode.includes('ARBITRAGE')) return 'badge-amber'
  if (mode.includes('CHARGING')) return 'badge-cyan'
  return 'badge-emerald'
})

onMounted(() => {
  initGauge()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (gaugeChart) gaugeChart.dispose()
})

watch(socPct, (newVal) => {
  if (!gaugeChart) return
  gaugeChart.setOption({
    series: [{ data: [{ value: newVal }] }]
  })
})

function initGauge() {
  if (!gaugeRef.value) return
  gaugeChart = echarts.init(gaugeRef.value)

  const option = {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        splitNumber: 5,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#f43f5e' },
            { offset: 0.3, color: '#f59e0b' },
            { offset: 0.7, color: '#10b981' },
            { offset: 1, color: '#06b6d4' }
          ])
        },
        progress: {
          show: true,
          roundCap: true,
          width: 12
        },
        pointer: { show: false },
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: 12,
            color: [[1, 'rgba(255, 255, 255, 0.08)']]
          }
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: { show: false },
        detail: { show: false },
        data: [{ value: socPct.value }]
      }
    ]
  }

  gaugeChart.setOption(option)
}

function handleResize() {
  if (gaugeChart) gaugeChart.resize()
}
</script>

<style scoped>
.bess-card {
  display: flex;
  flex-direction: column;
  height: 380px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-amber { background: rgba(245, 158, 11, 0.1); }
.text-amber { color: var(--accent-amber); }

.card-title {
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.bess-body {
  display: flex;
  align-items: center;
  flex: 1;
  padding: 16px 20px;
  gap: 20px;
}

.soc-gauge-col {
  position: relative;
  width: 180px;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gauge-wrap {
  width: 100%;
  height: 100%;
}

.soc-label-center {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.soc-num {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

.soc-sub {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.flow-stats-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.flow-metric-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.metric-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  padding: 12px 14px;
  border-radius: 8px;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 4px;
}

.metric-val {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  display: block;
}

.metric-hint {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 4px;
  display: block;
}

.text-cyan { color: var(--accent-cyan); }
.text-rose { color: var(--accent-rose); }
.text-emerald { color: var(--accent-emerald); }
</style>
