<template>
  <div class="glass-panel scenario-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-cyan">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </div>
        <div>
          <h3 class="card-title">Grid Disturbance & Fault Simulator</h3>
          <p class="card-subtitle">Inject Dynamic Weather Events, Inverter String Trips & Tariff Surges</p>
        </div>
      </div>
      <div class="header-right">
        <button @click="resetAll" class="btn-scada" :disabled="loading">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
          Reset All
        </button>
      </div>
    </div>

    <div class="scenario-body">
      <div class="scenario-grid">
        <!-- Passing Cloud -->
        <button 
          @click="trigger('cloud_cover', { drop_pct: 75, duration_sec: 40 })" 
          class="scenario-btn btn-cloud"
          :disabled="loading"
        >
          <div class="s-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
          </div>
          <div class="s-text">
            <span class="s-title">Passing Cloud Cover</span>
            <span class="s-desc">-75% Irradiance (40s)</span>
          </div>
        </button>

        <!-- Wind Lull -->
        <button 
          @click="trigger('wind_lull', { drop_pct: 70, duration_sec: 30 })" 
          class="scenario-btn btn-wind"
          :disabled="loading"
        >
          <div class="s-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>
          </div>
          <div class="s-text">
            <span class="s-title">Sudden Wind Lull</span>
            <span class="s-desc">-70% Wind Speed (30s)</span>
          </div>
        </button>

        <!-- Wind Gust -->
        <button 
          @click="trigger('wind_gust', { boost_pct: 60, duration_sec: 30 })" 
          class="scenario-btn btn-gust"
          :disabled="loading"
        >
          <div class="s-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          </div>
          <div class="s-text">
            <span class="s-title">Wind Turbine Gust</span>
            <span class="s-desc">+60% Wind (Surplus Absorption)</span>
          </div>
        </button>

        <!-- Trip String 3 Fuse -->
        <button 
          @click="trigger('string_fault', { inverter_id: 'INV-02', string_id: 'STR-03', fault_type: 'BLOWN_FUSE' })" 
          class="scenario-btn btn-fault"
          :disabled="loading"
        >
          <div class="s-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
          </div>
          <div class="s-text">
            <span class="s-title">Trip String #3 Fuse</span>
            <span class="s-desc">INV-02:STR-03 (0V Mismatch)</span>
          </div>
        </button>

        <!-- Inverter Overheat -->
        <button 
          @click="trigger('inverter_overheat', { inverter_id: 'INV-01', temp_c: 96.5 })" 
          class="scenario-btn btn-heat"
          :disabled="loading"
        >
          <div class="s-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/></svg>
          </div>
          <div class="s-text">
            <span class="s-title">Inverter Overheat</span>
            <span class="s-desc">INV-01 Thermal Trip (96.5°C)</span>
          </div>
        </button>

        <!-- Tariff Spike -->
        <button 
          @click="trigger('tariff_spike', { tariff_usd: 0.58, duration_sec: 60 })" 
          class="scenario-btn btn-tariff"
          :disabled="loading"
        >
          <div class="s-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          </div>
          <div class="s-text">
            <span class="s-title">Tariff Surge Spike</span>
            <span class="s-desc">$0.58/kWh (Peak Arbitrage)</span>
          </div>
        </button>
      </div>

      <!-- Live Notification Banner -->
      <div v-if="feedbackMsg" class="feedback-banner">
        <span class="status-dot active"></span>
        <span>{{ feedbackMsg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['trigger-disturbance', 'reset-disturbances'])
const loading = ref(false)
const feedbackMsg = ref('')

async function trigger(type, params = {}) {
  loading.value = true
  try {
    const res = await fetch('/api/simulate/disturbance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disturbance_type: type, ...params })
    })
    const data = await res.json()
    feedbackMsg.value = data.message || 'Disturbance successfully applied.'
    emit('trigger-disturbance', data)
  } catch (err) {
    feedbackMsg.value = 'Failed to apply disturbance: ' + err.message
  } finally {
    loading.value = false
    setTimeout(() => { feedbackMsg.value = '' }, 5000)
  }
}

async function resetAll() {
  loading.value = true
  try {
    const res = await fetch('/api/simulate/reset', { method: 'POST' })
    const data = await res.json()
    feedbackMsg.value = data.message || 'Disturbances reset.'
    emit('reset-disturbances', data)
  } catch (err) {
    feedbackMsg.value = 'Failed to reset: ' + err.message
  } finally {
    loading.value = false
    setTimeout(() => { feedbackMsg.value = '' }, 4000)
  }
}
</script>

<style scoped>
.scenario-card {
  display: flex;
  flex-direction: column;
  height: 340px;
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
.icon-cyan { background: rgba(6, 182, 212, 0.1); }
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

.scenario-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.scenario-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  color: var(--text-primary);
}

.scenario-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.s-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
}

.btn-cloud:hover { border-color: var(--accent-cyan); }
.btn-cloud .s-icon { color: var(--accent-cyan); }

.btn-wind:hover { border-color: var(--accent-emerald); }
.btn-wind .s-icon { color: var(--accent-emerald); }

.btn-gust:hover { border-color: var(--accent-amber); }
.btn-gust .s-icon { color: var(--accent-amber); }

.btn-fault:hover { border-color: var(--accent-rose); }
.btn-fault .s-icon { color: var(--accent-rose); }

.btn-heat:hover { border-color: var(--accent-rose); }
.btn-heat .s-icon { color: var(--accent-rose); }

.btn-tariff:hover { border-color: var(--accent-amber); }
.btn-tariff .s-icon { color: var(--accent-amber); }

.s-text {
  display: flex;
  flex-direction: column;
}

.s-title {
  font-size: 0.78rem;
  font-weight: 600;
}

.s-desc {
  font-size: 0.68rem;
  color: var(--text-muted);
}

.feedback-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 6px;
  font-size: 0.78rem;
  color: var(--accent-cyan);
}

@media (max-width: 992px) {
  .scenario-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
