<template>
  <div v-if="isOpen" class="modal-backdrop" @keydown.esc="close" tabindex="0">
    <div class="modal-card">
      <!-- Header -->
      <div class="modal-header">
        <div class="modal-title-wrap">
          <div class="modal-icon-wrap">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><rect width="16" height="10" x="2" y="7" rx="2" ry="2"/><line x1="22" x2="22" y1="11" y2="13"/></svg>
          </div>
          <div>
            <div class="modal-title">
              BESS ELECTROCHEMICAL HEALTH <span class="text-cyan">// 2RC THEVENIN ECM & THERMAL RUNAWAY SAFETY</span>
            </div>
            <div class="modal-subtitle">
              10.0 MWh / 5.0 MW LiFePO4 • 4 Megapacks • 16 Racks • NFPA 855 / UL 9540A Compliant
            </div>
          </div>
        </div>

        <!-- SOH & Interlock Badges -->
        <div class="header-badges">
          <div class="h-badge">
            <span class="hb-lbl">SOH (CAPACITY)</span>
            <span class="hb-val mono-val text-emerald">{{ (bessHealth?.soh_capacity_pct || 98.4).toFixed(1) }}%</span>
          </div>
          <div class="h-badge">
            <span class="hb-lbl">SOH (RESISTANCE)</span>
            <span class="hb-val mono-val text-emerald">{{ (bessHealth?.soh_resistance_pct || 96.0).toFixed(1) }}%</span>
          </div>
          <div class="h-badge">
            <span class="hb-lbl">R₀ OHMIC</span>
            <span class="hb-val mono-val text-cyan">{{ (bessHealth?.r0_ohmic_mohm || 0.885).toFixed(3) }} mΩ</span>
          </div>
          <div class="h-badge" :class="interlockBadgeClass">
            <span class="hb-lbl">SAFETY INTERLOCK</span>
            <span class="hb-val">{{ isInterlockTripped ? 'TRIPPED ISOLATED' : 'CONTACTORS CLOSED' }}</span>
          </div>
          <button @click="close" class="modal-close-btn">&times;</button>
        </div>
      </div>

      <!-- Main Body -->
      <div class="modal-body">
        <!-- Left: 16-Rack Cell Matrix Heatmap -->
        <div class="racks-col">
          <div class="section-title-wrap">
            <span class="section-title">16-RACK CELL MATRIX & THERMAL TOPOLOGY</span>
            <span class="section-sub">Max Cell Temp: <span class="mono-val text-cyan">{{ (bessHealth?.max_cell_temp_c || 25.1).toFixed(1) }}°C</span></span>
          </div>

          <div class="racks-grid">
            <div 
              v-for="rack in racksList" 
              :key="rack.rack_id" 
              class="rack-card"
              :class="getRackCardClass(rack)"
              @click="selectedRack = rack"
            >
              <div class="rack-header">
                <span class="rack-id">{{ rack.rack_id }}</span>
                <span class="rack-status-dot" :class="getRackDotClass(rack)"></span>
              </div>
              <div class="rack-metrics">
                <div class="r-metric">
                  <span class="rm-lbl">MAX TEMP</span>
                  <span class="rm-val mono-val" :class="rack.max_cell_temp_c > 45 ? 'text-rose' : 'text-emerald'">
                    {{ rack.max_cell_temp_c.toFixed(1) }}°C
                  </span>
                </div>
                <div class="r-metric">
                  <span class="rm-lbl">SPREAD (ΔV)</span>
                  <span class="rm-val mono-val" :class="rack.voltage_spread_mv > 20 ? 'text-rose' : 'text-slate'">
                    {{ rack.voltage_spread_mv.toFixed(0) }} mV
                  </span>
                </div>
              </div>
              <div class="rack-footer">
                <span class="contactor-tag" :class="rack.contactor_status === 'TRIPPED_ISOLATED' ? 'tag-tripped' : 'tag-closed'">
                  {{ rack.contactor_status === 'TRIPPED_ISOLATED' ? 'ISOLATED' : 'ONLINE' }}
                </span>
                <span v-if="rack.stage !== 'STAGE_0_NORMAL'" class="stage-tag">
                  {{ rack.stage }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Nyquist Impedance Plot + Off-Gas Sensors & Drill Controls -->
        <div class="diagnostics-col">
          <!-- Nyquist Plot Card -->
          <div class="nyquist-card">
            <div class="card-inner-header">
              <span class="card-inner-title">ELECTROCHEMICAL IMPEDANCE SPECTROSCOPY (EIS) // NYQUIST PLOT</span>
              <span class="card-inner-sub">Fresh Cell vs Current Degraded Cell</span>
            </div>
            <div ref="nyquistChartEl" class="nyquist-chart"></div>
          </div>

          <!-- Off-Gas Sensor Array Card -->
          <div class="offgas-card">
            <div class="card-inner-header">
              <span class="card-inner-title">NFPA 855 OFF-GAS DETECTOR ARRAY</span>
              <span class="gas-alarm-badge" :class="isGasAlarm ? 'badge-rose-pulse' : 'badge-emerald'">
                {{ isGasAlarm ? '⚠️ OFF-GAS ALARM' : 'NORMAL' }}
              </span>
            </div>

            <div class="gas-meters-grid">
              <!-- Hydrogen (H2) -->
              <div class="gas-meter">
                <div class="gm-top">
                  <span class="gm-name">Hydrogen (H₂)</span>
                  <span class="gm-val mono-val" :class="h2Ppm > 20 ? 'text-rose' : 'text-cyan'">{{ h2Ppm.toFixed(1) }} <small>ppm</small></span>
                </div>
                <div class="gm-track">
                  <div class="gm-bar" :style="{ width: `${Math.min(100, (h2Ppm / 40.0) * 100)}%`, background: h2Ppm > 20 ? '#ef4444' : '#06b6d4' }"></div>
                  <div class="gm-threshold-line" style="left: 50%;"></div>
                </div>
                <div class="gm-sub">Threshold: 20.0 ppm</div>
              </div>

              <!-- Carbon Monoxide (CO) -->
              <div class="gas-meter">
                <div class="gm-top">
                  <span class="gm-name">Carbon Monoxide (CO)</span>
                  <span class="gm-val mono-val" :class="coPpm > 15 ? 'text-rose' : 'text-cyan'">{{ coPpm.toFixed(1) }} <small>ppm</small></span>
                </div>
                <div class="gm-track">
                  <div class="gm-bar" :style="{ width: `${Math.min(100, (coPpm / 30.0) * 100)}%`, background: coPpm > 15 ? '#ef4444' : '#06b6d4' }"></div>
                  <div class="gm-threshold-line" style="left: 50%;"></div>
                </div>
                <div class="gm-sub">Threshold: 15.0 ppm</div>
              </div>

              <!-- VOC -->
              <div class="gas-meter">
                <div class="gm-top">
                  <span class="gm-name">Electrolyte VOC</span>
                  <span class="gm-val mono-val">{{ vocPpm.toFixed(1) }} <small>ppm</small></span>
                </div>
                <div class="gm-track">
                  <div class="gm-bar" :style="{ width: `${Math.min(100, (vocPpm / 50.0) * 100)}%`, background: '#10b981' }"></div>
                </div>
                <div class="gm-sub">Threshold: 25.0 ppm</div>
              </div>
            </div>

            <!-- Drill Buttons -->
            <div class="drill-actions">
              <button @click="triggerDrill" class="btn-drill btn-drill-trigger" :disabled="isActing">
                🔥 Simulate Cell Micro-Short & Off-Gassing Drill
              </button>
              <button @click="resetDrill" class="btn-drill btn-drill-reset" :disabled="isActing">
                ↺ Reset BESS Health & Reclose Contactors
              </button>
            </div>
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

const nyquistChartEl = ref(null)
let nyquistChart = null
const isActing = ref(false)
const selectedRack = ref(null)

const bessHealth = computed(() => props.telemetry?.bess_health || {})
const racksList = computed(() => bessHealth.value?.racks || [])
const isInterlockTripped = computed(() => Boolean(bessHealth.value?.emergency_contactor_tripped))

const h2Ppm = computed(() => bessHealth.value?.off_gas_sensors?.h2_ppm ?? 1.2)
const coPpm = computed(() => bessHealth.value?.off_gas_sensors?.co_ppm ?? 0.8)
const vocPpm = computed(() => bessHealth.value?.off_gas_sensors?.voc_ppm ?? 4.5)
const isGasAlarm = computed(() => Boolean(bessHealth.value?.off_gas_sensors?.alarm_active))

const interlockBadgeClass = computed(() => {
  return isInterlockTripped.value ? 'badge-rose-pulse' : 'badge-emerald'
})

function getRackCardClass(rack) {
  if (rack.contactor_status === 'TRIPPED_ISOLATED') return 'rack-tripped'
  if (rack.max_cell_temp_c > 45.0) return 'rack-critical'
  if (rack.max_cell_temp_c > 30.0) return 'rack-warning'
  return ''
}

function getRackDotClass(rack) {
  if (rack.contactor_status === 'TRIPPED_ISOLATED') return 'dot-tripped'
  if (rack.max_cell_temp_c > 45.0) return 'dot-critical'
  if (rack.max_cell_temp_c > 30.0) return 'dot-warning'
  return 'dot-normal'
}

function initNyquistChart() {
  if (!nyquistChartEl.value) return
  nyquistChart = echarts.init(nyquistChartEl.value)
  renderNyquistChart()
  window.addEventListener('resize', handleResize)
}

function renderNyquistChart() {
  if (!nyquistChart) return

  // Synthetic Nyquist semicircles:
  // Fresh cell: R0 = 0.85 mOhm, Arc radius = 0.6 mOhm (peaks at Z' = 1.45, -Z'' = 0.6)
  // Current degraded cell: R0 = 0.885 mOhm, Arc radius = 0.8 mOhm
  const freshData = []
  const currentData = []

  // Generate semicircle points
  for (let angle = 0; angle <= 180; angle += 5) {
    const rad = (angle * Math.PI) / 180.0
    // Fresh
    const z_real_fresh = 0.85 + 0.60 * (1.0 - Math.cos(rad))
    const z_imag_fresh = 0.60 * Math.sin(rad)
    freshData.push([z_real_fresh, z_imag_fresh])

    // Current
    const r0_curr = bessHealth.value?.r0_ohmic_mohm || 0.885
    const z_real_curr = r0_curr + 0.75 * (1.0 - Math.cos(rad))
    const z_imag_curr = 0.75 * Math.sin(rad)
    currentData.push([z_real_curr, z_imag_curr])
  }

  // Add low-frequency 45 deg Warburg diffusion tail
  for (let d = 0; d <= 5; d++) {
    const lastFresh = freshData[freshData.length - 1]
    freshData.push([lastFresh[0] + d * 0.15, lastFresh[1] + d * 0.15])

    const lastCurr = currentData[currentData.length - 1]
    currentData.push([lastCurr[0] + d * 0.18, lastCurr[1] + d * 0.18])
  }

  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '12%',
      right: '8%',
      top: '12%',
      bottom: '18%'
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(11, 19, 36, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      formatter: (params) => {
        return `${params.seriesName}<br/>Z' (Real): ${params.data[0].toFixed(3)} mΩ<br/>-Z'' (Imag): ${params.data[1].toFixed(3)} mΩ`
      },
      textStyle: { color: '#f1f5f9', fontSize: 11, fontFamily: 'JetBrains Mono' }
    },
    xAxis: {
      type: 'value',
      name: "Z' Real (mΩ)",
      min: 0.5,
      max: 3.5,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#64748b', fontSize: 9, fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } }
    },
    yAxis: {
      type: 'value',
      name: "-Z'' Imag (mΩ)",
      min: 0,
      max: 1.8,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#64748b', fontSize: 9, fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } }
    },
    series: [
      {
        name: 'Fresh Factory Baseline',
        type: 'line',
        data: freshData,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#64748b', type: 'dashed', width: 1.5 }
      },
      {
        name: 'Current LiFePO4 Impedance',
        type: 'line',
        data: currentData,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#06b6d4', width: 2.5 }
      }
    ]
  }

  nyquistChart.setOption(option)
}

function handleResize() {
  nyquistChart?.resize()
}

async function triggerDrill() {
  isActing.value = true
  try {
    await fetch('/api/bess/thermal-drill', { method: 'POST' })
  } catch (err) {
    console.error('Failed to trigger BESS thermal drill:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 2000)
  }
}

async function resetDrill() {
  isActing.value = true
  try {
    await fetch('/api/bess/reset', { method: 'POST' })
  } catch (err) {
    console.error('Failed to reset BESS health:', err)
  } finally {
    setTimeout(() => { isActing.value = false }, 1000)
  }
}

function close() {
  emit('close')
}

watch(() => props.isOpen, (open) => {
  if (open) {
    setTimeout(() => {
      initNyquistChart()
    }, 100)
  }
})

watch(() => bessHealth.value?.r0_ohmic_mohm, () => {
  if (nyquistChart) {
    renderNyquistChart()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  nyquistChart?.dispose()
})
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
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8);
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
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.3);
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
.badge-rose-pulse {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.6);
  color: #ef4444;
  animation: pulseAlarm 1s infinite;
}

@keyframes pulseAlarm {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

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

/* Body */
.modal-body {
  flex: 1;
  display: flex;
  padding: 1.25rem;
  gap: 1.25rem;
  overflow: hidden;
}

/* Left Racks Grid */
.racks-col {
  flex: 1.4;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.section-title-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
}

.section-sub {
  font-size: 0.72rem;
  color: #64748b;
}

.racks-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
}

.rack-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 0.65rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.rack-card:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(6, 182, 212, 0.4);
}

.rack-tripped {
  background: rgba(239, 68, 68, 0.12) !important;
  border-color: rgba(239, 68, 68, 0.5) !important;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.2);
}

.rack-critical {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.35);
}

.rack-warning {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.35);
}

.rack-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rack-id {
  font-size: 0.72rem;
  font-weight: 700;
  color: #f1f5f9;
  font-family: 'JetBrains Mono', monospace;
}

.rack-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-normal { background: #10b981; }
.dot-warning { background: #f59e0b; }
.dot-critical { background: #ef4444; }
.dot-tripped { background: #ef4444; box-shadow: 0 0 8px #ef4444; }

.rack-metrics {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
}

.r-metric {
  display: flex;
  flex-direction: column;
}

.rm-lbl {
  font-size: 0.55rem;
  color: #64748b;
}

.rm-val {
  font-weight: 700;
}

.rack-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.6rem;
  margin-top: 0.2rem;
}

.contactor-tag {
  font-size: 0.55rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

.tag-closed { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.tag-tripped { background: rgba(239, 68, 68, 0.3); color: #ef4444; }

.stage-tag {
  font-size: 0.55rem;
  color: #ef4444;
  font-weight: 700;
}

/* Right Diagnostics Col */
.diagnostics-col {
  flex: 1.6;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.nyquist-card, .offgas-card {
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
  font-size: 0.65rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.nyquist-chart {
  width: 100%;
  height: 200px;
}

/* Off-gas meters */
.gas-alarm-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.gas-meters-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.gas-meter {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 0.5rem 0.65rem;
}

.gm-top {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
  margin-bottom: 0.35rem;
}

.gm-name { color: #94a3b8; }
.gm-val { font-weight: 700; }

.gm-track {
  position: relative;
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.gm-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.gm-threshold-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ef4444;
}

.gm-sub {
  font-size: 0.58rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
  margin-top: 0.25rem;
}

/* Drill Actions */
.drill-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-drill {
  flex: 1;
  padding: 0.5rem 0.8rem;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.btn-drill-trigger {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.35);
  color: #ef4444;
}

.btn-drill-trigger:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.25);
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
}

.btn-drill-reset {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.btn-drill-reset:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
}

.btn-drill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1024px) {
  .modal-body {
    flex-direction: column;
  }
}
</style>
