<template>
  <div class="glass-panel forecast-curve-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-cyan">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
        </div>
        <div>
          <h3 class="card-title">Probabilistic Quantile Forecast (P10 / P50 / P90)</h3>
          <p class="card-subtitle">LightGBM Multi-Quantile Exceedance Horizon • P90 Contractual Safety Band</p>
        </div>
      </div>
      <div class="header-right">
        <div class="legend-badges">
          <span class="legend-chip chip-cyan"><span class="chip-dot bg-cyan"></span> P50 (Expected)</span>
          <span class="legend-chip chip-p90"><span class="chip-dot bg-p90"></span> P90 (Safe Bidding)</span>
          <span class="legend-chip chip-p10"><span class="chip-dot bg-p10"></span> P10 (Optimistic)</span>
          <span class="legend-chip chip-amber"><span class="chip-dot bg-amber"></span> Schedule</span>
          <span class="legend-chip chip-emerald"><span class="chip-dot bg-emerald"></span> Actual Injected</span>
        </div>
      </div>
    </div>

    <!-- Uncertainty Spread Metric Bar -->
    <div class="uncertainty-bar" v-if="latestSpread > 0">
      <div class="u-metric">
        <span class="u-label">P90 Safe Commitment:</span>
        <span class="u-val mono-val">{{ Math.round(latestP90).toLocaleString() }} kW</span>
      </div>
      <div class="u-metric">
        <span class="u-label">P50 Expected Median:</span>
        <span class="u-val mono-val text-cyan">{{ Math.round(latestP50).toLocaleString() }} kW</span>
      </div>
      <div class="u-metric">
        <span class="u-label">P10 Optimistic Upside:</span>
        <span class="u-val mono-val">{{ Math.round(latestP10).toLocaleString() }} kW</span>
      </div>
      <div class="u-metric">
        <span class="u-label">Quantile Uncertainty Spread (P10-P90):</span>
        <span class="u-val mono-val text-amber">±{{ Math.round(latestSpread / 2).toLocaleString() }} kW</span>
      </div>
      <div class="u-metric" v-if="riskLevel">
        <span class="u-label">Shortfall Penalty Risk:</span>
        <span class="badge" :class="riskLevel.includes('HIGH') ? 'badge-rose' : (riskLevel.includes('MODERATE') ? 'badge-amber' : 'badge-emerald')">
          {{ riskLevel.replace(/_/g, ' ') }}
        </span>
      </div>
    </div>

    <div class="chart-container" ref="chartRef"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  history: {
    type: Array,
    default: () => []
  },
  latest: {
    type: Object,
    default: () => ({})
  }
})

const chartRef = ref(null)
let myChart = null

const latestP90 = computed(() => props.latest?.forecast_15m?.p90_conservative_kw || 0)
const latestP50 = computed(() => props.latest?.forecast_15m?.p50_median_kw || props.latest?.forecast_15m?.predicted_total_kw || 0)
const latestP10 = computed(() => props.latest?.forecast_15m?.p10_optimistic_kw || 0)
const latestSpread = computed(() => props.latest?.forecast_15m?.uncertainty_spread_kw || 0)
const riskLevel = computed(() => props.latest?.bess_dispatch?.risk_level || 'BALANCED')

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (myChart) myChart.dispose()
})

watch(() => props.history, (newHistory) => {
  if (!myChart || !newHistory.length) return
  updateChartData(newHistory)
}, { deep: true })

function initChart() {
  if (!chartRef.value) return
  myChart = echarts.init(chartRef.value)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13, 17, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#f1f5f9', fontFamily: 'JetBrains Mono', fontSize: 12 },
      formatter: (params) => {
        if (!params.length) return ''
        let res = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:4px;">${params[0].axisValue}</div>`
        params.forEach(p => {
          if (p.seriesName === 'P90 Base') return // Skip helper stack series
          res += `<div style="display:flex;justify-content:space-between;gap:16px;padding:2px 0;">
            <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}:</span>
            <span style="font-weight:700;">${p.value !== undefined ? p.value.toLocaleString() + ' kW' : '--'}</span>
          </div>`
        })
        return res
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '10%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: '#64748b', fontFamily: 'JetBrains Mono', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: 'Power (kW)',
      nameTextStyle: { color: '#64748b', fontSize: 11, padding: [0, 0, 0, 20] },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontFamily: 'JetBrains Mono', fontSize: 11 }
    },
    series: [
      // 1. P90 Base Line (Lower Exceedance Bound)
      {
        name: 'P90 (Conservative)',
        type: 'line',
        smooth: true,
        data: [],
        lineStyle: { width: 1.5, color: '#38bdf8', type: 'dashed' },
        itemStyle: { color: '#38bdf8' },
        showSymbol: false,
        z: 2
      },
      // 2. P10 Optimistic (Upper Exceedance Bound with translucent fan area)
      {
        name: 'P10 (Optimistic)',
        type: 'line',
        smooth: true,
        data: [],
        lineStyle: { width: 1.5, color: '#818cf8', type: 'dashed' },
        itemStyle: { color: '#818cf8' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(129, 140, 248, 0.18)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0.05)' }
          ])
        },
        showSymbol: false,
        z: 1
      },
      // 3. P50 Median Expected Forecast
      {
        name: 'P50 (Expected Median)',
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 2.5, color: '#06b6d4', shadowColor: 'rgba(6, 182, 212, 0.5)', shadowBlur: 8 },
        showSymbol: false,
        z: 4
      },
      // 4. Committed Schedule (PPA)
      {
        name: 'Committed Schedule',
        type: 'line',
        step: 'end',
        data: [],
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 2, type: 'dashed', color: '#f59e0b' },
        showSymbol: false,
        z: 3
      },
      // 5. Actual Injected Generation
      {
        name: 'Actual Injected',
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 2.5, color: '#10b981', shadowColor: 'rgba(16, 185, 129, 0.5)', shadowBlur: 8 },
        showSymbol: false,
        z: 5
      }
    ]
  }

  myChart.setOption(option)
}

function updateChartData(history) {
  const times = []
  const p90s = []
  const p10s = []
  const p50s = []
  const schedules = []
  const actuals = []

  history.slice(-30).forEach(p => {
    const d = new Date(p.timestamp)
    times.push(d.toTimeString().split(' ')[0])
    
    const fc = p.forecast_15m || {}
    p90s.push(fc.p90_conservative_kw || Math.max(0, (fc.predicted_total_kw || 0) * 0.9))
    p10s.push(fc.p10_optimistic_kw || ((fc.predicted_total_kw || 0) * 1.1))
    p50s.push(fc.p50_median_kw || fc.predicted_total_kw || 0)
    schedules.push(p.committed_schedule_kw || 0)
    actuals.push(p.bess_dispatch?.final_injected_kw || p.total_renewable_kw || 0)
  })

  myChart.setOption({
    xAxis: { data: times },
    series: [
      { data: p90s },
      { data: p10s },
      { data: p50s },
      { data: schedules },
      { data: actuals }
    ]
  })
}

function handleResize() {
  if (myChart) myChart.resize()
}
</script>

<style scoped>
.forecast-curve-card {
  display: flex;
  flex-direction: column;
  height: 420px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
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
.icon-cyan {
  background: rgba(6, 182, 212, 0.1);
}
.text-cyan { color: var(--accent-cyan); }

.card-title {
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.legend-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.legend-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  font-weight: 500;
  padding: 3px 7px;
  border-radius: 6px;
}
.chip-cyan { background: rgba(6, 182, 212, 0.1); color: var(--accent-cyan); }
.chip-p90 { background: rgba(56, 189, 248, 0.1); color: #38bdf8; }
.chip-p10 { background: rgba(129, 140, 248, 0.1); color: #818cf8; }
.chip-amber { background: rgba(245, 158, 11, 0.1); color: var(--accent-amber); }
.chip-emerald { background: rgba(16, 185, 129, 0.1); color: var(--accent-emerald); }

.chip-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.bg-cyan { background: var(--accent-cyan); }
.bg-p90 { background: #38bdf8; }
.bg-p10 { background: #818cf8; }
.bg-amber { background: var(--accent-amber); }
.bg-emerald { background: var(--accent-emerald); }

.uncertainty-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-color);
  font-size: 0.75rem;
}

.u-metric {
  display: flex;
  align-items: center;
  gap: 6px;
}

.u-label {
  color: var(--text-muted);
}

.u-val {
  font-weight: 700;
  color: var(--text-primary);
}

.chart-container {
  flex: 1;
  width: 100%;
  height: 100%;
}
</style>
