<template>
  <div class="glass-panel alerts-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-rose">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-rose"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
        </div>
        <div>
          <h3 class="card-title">Inverter Health & SCADA Alert Stream</h3>
          <p class="card-subtitle">Real-Time Inverter String Diagnostics & Grid Compliance</p>
        </div>
      </div>
      <div class="header-right">
        <span class="badge" :class="activeAlerts.length > 0 ? 'badge-rose' : 'badge-emerald'">
          {{ activeAlerts.length }} Active
        </span>
      </div>
    </div>

    <div class="alerts-body">
      <div v-if="!activeAlerts.length" class="empty-alerts">
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-emerald"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <span>All 4 Inverters and 32 Strings Operating Within Normal Parameters</span>
      </div>

      <div v-else class="alerts-list">
        <div 
          v-for="(alert, idx) in activeAlerts" 
          :key="idx" 
          class="alert-item"
          :class="alert.severity === 'CRITICAL' ? 'item-critical' : 'item-warning'"
        >
          <div class="alert-top">
            <span class="badge" :class="alert.severity === 'CRITICAL' ? 'badge-rose' : 'badge-amber'">
              {{ alert.severity }}
            </span>
            <span class="alert-target mono-val">
              {{ alert.inverter_id }} <template v-if="alert.string_id">: {{ alert.string_id }}</template>
            </span>
            <span class="alert-time mono-val">{{ formatTime(alert.detected_at) }}</span>
          </div>

          <p class="alert-msg">{{ alert.message }}</p>

          <div class="alert-actions">
            <span class="type-tag mono-val">{{ alert.alert_type }}</span>
            <button 
              v-if="alert.status !== 'ACKNOWLEDGED'" 
              @click="acknowledge(alert)" 
              class="btn-scada btn-scada-rose btn-ack"
            >
              Acknowledge
            </button>
            <span v-else class="ack-tag">ACKNOWLEDGED</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  alerts: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['acknowledge'])

const activeAlerts = computed(() => props.alerts || [])

function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toTimeString().split(' ')[0]
  } catch {
    return isoStr
  }
}

function acknowledge(alert) {
  emit('acknowledge', alert)
}
</script>

<style scoped>
.alerts-card {
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
.icon-rose { background: rgba(244, 63, 94, 0.1); }
.text-rose { color: var(--accent-rose); }
.text-emerald { color: var(--accent-emerald); }

.card-title {
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.alerts-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
}

.empty-alerts {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 10px;
  color: var(--text-muted);
  font-size: 0.82rem;
  text-align: center;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px 14px;
}

.alert-item.item-critical {
  border-color: rgba(244, 63, 94, 0.4);
  background: rgba(244, 63, 94, 0.08);
}

.alert-item.item-warning {
  border-color: rgba(245, 158, 11, 0.35);
  background: rgba(245, 158, 11, 0.06);
}

.alert-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.alert-target {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

.alert-time {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-left: auto;
}

.alert-msg {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-bottom: 8px;
}

.alert-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-tag {
  font-size: 0.65rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 6px;
  border-radius: 4px;
}

.btn-ack {
  padding: 3px 10px;
  font-size: 0.72rem;
}

.ack-tag {
  font-size: 0.68rem;
  color: var(--accent-cyan);
  font-weight: 600;
}
</style>
