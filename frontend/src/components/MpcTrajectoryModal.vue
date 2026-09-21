<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="close">
    <div class="mpc-modal glass-panel">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-left">
          <div class="icon-wrap icon-cyan">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          </div>
          <div>
            <h2 class="modal-title">4-Hour Model Predictive Control (MPC) Horizon</h2>
            <p class="modal-subtitle">HiGHS Linear Programming Solver • Forward Lookahead & LiFePO4 Degradation Cost</p>
          </div>
        </div>
        <div class="header-right">
          <button @click="fetchPlan" class="btn-scada btn-scada-cyan btn-refresh" :disabled="loading">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            Recalculate
          </button>
          <button @click="close" class="close-btn">&times;</button>
        </div>
      </div>

      <!-- Economic KPI Strip -->
      <div class="kpi-strip" v-if="plan?.summary">
        <div class="kpi-box">
          <span class="kpi-lbl">4H Projected Revenue</span>
          <span class="kpi-val mono-val text-emerald">${{ Math.round(plan.summary.projected_revenue_usd).toLocaleString() }}</span>
          <span class="kpi-sub">Grid Injection PPA</span>
        </div>
        <div class="kpi-box">
          <span class="kpi-lbl">Avoided Deviation Penalties</span>
          <span class="kpi-val mono-val text-cyan">${{ Math.round(plan.summary.projected_penalties_usd).toLocaleString() }}</span>
          <span class="kpi-sub">Contractual Non-Compliance</span>
        </div>
        <div class="kpi-box">
          <span class="kpi-lbl">Cell Degradation Cost</span>
          <span class="kpi-val mono-val text-rose">-${{ Math.round(plan.summary.projected_degradation_usd).toLocaleString() }}</span>
          <span class="kpi-sub">$0.022/kWh Throughput</span>
        </div>
        <div class="kpi-box">
          <span class="kpi-lbl">Net Optimized Benefit</span>
          <span class="kpi-val mono-val text-amber">${{ Math.round(plan.summary.net_profit_usd).toLocaleString() }}</span>
          <span class="kpi-sub">Revenue - Penalties - Deg</span>
        </div>
      </div>

      <!-- Dual-Axis ECharts MPC Horizon Curve -->
      <div class="chart-box">
        <div class="chart-container" ref="chartRef"></div>
      </div>

      <!-- Intervals Table -->
      <div class="table-container">
        <table class="mpc-table">
          <thead>
            <tr>
              <th>Interval</th>
              <th>Forecast (kW)</th>
              <th>Schedule (kW)</th>
              <th>Tariff ($/kWh)</th>
              <th>Optimal BESS (kW)</th>
              <th>Net Injected (kW)</th>
              <th>Predicted SoC</th>
              <th>Revenue ($)</th>
              <th>Deg Cost ($)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in plan?.intervals || []" :key="row.step_index">
              <td class="mono-val font-bold">{{ row.time }}</td>
              <td class="mono-val">{{ Math.round(row.forecast_generation_kw).toLocaleString() }}</td>
              <td class="mono-val text-amber">{{ Math.round(row.committed_schedule_kw).toLocaleString() }}</td>
              <td class="mono-val">${{ row.tariff_usd_kwh.toFixed(3) }}</td>
              <td class="mono-val font-bold" :class="row.optimal_bess_kw > 0 ? 'text-amber' : (row.optimal_bess_kw < 0 ? 'text-cyan' : '')">
                {{ row.optimal_bess_kw > 0 ? '+' : '' }}{{ Math.round(row.optimal_bess_kw).toLocaleString() }}
              </td>
              <td class="mono-val text-emerald">{{ Math.round(row.optimal_injected_kw).toLocaleString() }}</td>
              <td class="mono-val">{{ row.predicted_soc_pct }}%</td>
              <td class="mono-val text-emerald">${{ Math.round(row.projected_revenue_usd).toLocaleString() }}</td>
              <td class="mono-val text-rose">-${{ row.projected_degradation_usd }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const chartRef = ref(null)
let myChart = null
const plan = ref(null)
const loading = ref(false)

onMounted(() => {
  if (props.isOpen) {
    fetchPlan()
  }
})

onUnmounted(() => {
  if (myChart) myChart.dispose()
})

watch(() => props.isOpen, (open) => {
  if (open) {
    fetchPlan()
  }
})

async function fetchPlan() {
  loading.value = true
  try {
    const res = await fetch('/api/dispatch/mpc-plan')
    const data = await res.json()
    plan.value = data
    setTimeout(initOrUpdateChart, 50)
  } catch (err) {
    console.error('Error fetching MPC dispatch plan:', err)
  } finally {
    loading.value = false
  }
}

function initOrUpdateChart() {
  if (!chartRef.value || !plan.value?.intervals) return
  if (!myChart) {
    myChart = echarts.init(chartRef.value)
  }

  const times = plan.value.intervals.map(i => i.time)
  const forecasts = plan.value.intervals.map(i => i.forecast_generation_kw)
  const schedules = plan.value.intervals.map(i => i.committed_schedule_kw)
  const bess = plan.value.intervals.map(i => i.optimal_bess_kw)
  const socs = plan.value.intervals.map(i => i.predicted_soc_pct)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13, 17, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#f1f5f9', fontFamily: 'JetBrains Mono', fontSize: 12 }
    },
    legend: {
      data: ['Committed Schedule', 'Forecast Generation', 'Optimal BESS Dispatch', 'Predicted Battery SoC'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '14%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: '#64748b', fontFamily: 'JetBrains Mono', fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: 'Power (kW)',
        nameTextStyle: { color: '#64748b', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)', type: 'dashed' } },
        axisLabel: { color: '#64748b', fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      {
        type: 'value',
        name: 'Battery SoC (%)',
        min: 0,
        max: 100,
        position: 'right',
        nameTextStyle: { color: '#a78bfa', fontSize: 11 },
        splitLine: { show: false },
        axisLabel: { color: '#a78bfa', fontFamily: 'JetBrains Mono', fontSize: 11, formatter: '{value}%' }
      }
    ],
    series: [
      {
        name: 'Committed Schedule',
        type: 'line',
        step: 'end',
        data: schedules,
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 2, type: 'dashed', color: '#f59e0b' }
      },
      {
        name: 'Forecast Generation',
        type: 'line',
        smooth: true,
        data: forecasts,
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 2, color: '#06b6d4', type: 'dotted' }
      },
      {
        name: 'Optimal BESS Dispatch',
        type: 'bar',
        data: bess,
        itemStyle: {
          color: (params) => params.value >= 0 ? '#f59e0b' : '#06b6d4'
        }
      },
      {
        name: 'Predicted Battery SoC',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: socs,
        itemStyle: { color: '#a78bfa' },
        lineStyle: { width: 2.5, color: '#a78bfa' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(167, 139, 250, 0.25)' },
            { offset: 1, color: 'rgba(167, 139, 250, 0.0)' }
          ])
        }
      }
    ]
  }

  myChart.setOption(option)
}

function close() {
  emit('close')
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.mpc-modal {
  width: 1000px;
  max-width: 95vw;
  max-height: 90vh;
  background: #0d111a;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-cyan { background: rgba(6, 182, 212, 0.12); }
.text-cyan { color: var(--accent-cyan); }
.text-emerald { color: var(--accent-emerald); }
.text-amber { color: var(--accent-amber); }
.text-rose { color: var(--accent-rose); }

.modal-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
}

.modal-subtitle {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-refresh {
  padding: 6px 12px;
  font-size: 0.75rem;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.8rem;
  cursor: pointer;
  line-height: 1;
}
.close-btn:hover { color: var(--text-primary); }

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-color);
}

.kpi-box {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  border-radius: 8px;
}

.kpi-lbl {
  font-size: 0.68rem;
  color: var(--text-muted);
  display: block;
}

.kpi-val {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 2px 0;
  display: block;
}

.kpi-sub {
  font-size: 0.68rem;
  color: var(--text-muted);
  display: block;
}

.chart-box {
  height: 280px;
  padding: 10px 24px;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.table-container {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px 20px 24px;
  max-height: 220px;
}

.mpc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}

.mpc-table th {
  position: sticky;
  top: 0;
  background: #0d111a;
  text-align: left;
  padding: 8px 10px;
  color: var(--text-muted);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.mpc-table td {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
}

.font-bold { font-weight: 700; }
</style>
