<template>
  <div class="glass-panel forecast-curve-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-cyan">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
        </div>
        <div>
          <h3 class="card-title">15-Min Rolling Yield Forecast vs. Grid Schedule</h3>
          <p class="card-subtitle">LightGBM Inference Path • Continuous 2s Real-Time Rolling Horizon</p>
        </div>
      </div>
      <div class="header-right">
        <div class="legend-badges">
          <span class="legend-chip chip-cyan"><span class="chip-dot bg-cyan"></span> 15m Forecast</span>
          <span class="legend-chip chip-emerald"><span class="chip-dot bg-emerald"></span> Actual Injected</span>
          <span class="legend-chip chip-amber"><span class="chip-dot bg-amber"></span> Committed Schedule</span>
        </div>
      </div>
    </div>

    <div class="chart-container" ref="chartRef"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
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
        let res = `<div style="font-weight:700;margin-bottom:4px;">${params[0].axisValue}</div>`
        params.forEach(p => {
          res += `<div style="display:flex;justify-content:space-between;gap:16px;">
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
      top: '12%',
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
      {
        name: 'Committed Schedule',
        type: 'line',
        step: 'end',
        data: [],
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 2, type: 'dashed', color: '#f59e0b' },
        showSymbol: false
      },
      {
        name: 'Actual Injected',
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 2.5, color: '#10b981', shadowColor: 'rgba(16, 185, 129, 0.5)', shadowBlur: 8 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.25)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.0)' }
          ])
        },
        showSymbol: false
      },
      {
        name: '15m Rolling Forecast',
        type: 'line',
        smooth: true,
        data: [],
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 2, color: '#06b6d4', type: 'dotted', shadowColor: 'rgba(6, 182, 212, 0.4)', shadowBlur: 6 },
        showSymbol: false
      }
    ]
  }

  myChart.setOption(option)
}

function updateChartData(history) {
  const times = []
  const schedules = []
  const actuals = []
  const forecasts = []

  history.slice(-30).forEach(p => {
    const d = new Date(p.timestamp)
    times.push(d.toTimeString().split(' ')[0])
    schedules.push(p.committed_schedule_kw || 0)
    actuals.push(p.bess_dispatch?.final_injected_kw || p.total_renewable_kw || 0)
    forecasts.push(p.forecast_15m?.predicted_total_kw || 0)
  })

  myChart.setOption({
    xAxis: { data: times },
    series: [
      { data: schedules },
      { data: actuals },
      { data: forecasts }
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
  gap: 10px;
}

.legend-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 6px;
}
.chip-cyan { background: rgba(6, 182, 212, 0.1); color: var(--accent-cyan); }
.chip-emerald { background: rgba(16, 185, 129, 0.1); color: var(--accent-emerald); }
.chip-amber { background: rgba(245, 158, 11, 0.1); color: var(--accent-amber); }

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.bg-cyan { background: var(--accent-cyan); }
.bg-emerald { background: var(--accent-emerald); }
.bg-amber { background: var(--accent-amber); }

.chart-container {
  flex: 1;
  width: 100%;
  height: 100%;
}
</style>
