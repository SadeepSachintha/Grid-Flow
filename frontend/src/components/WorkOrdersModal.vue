<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="close">
    <div class="work-orders-drawer glass-panel">
      <!-- Drawer Header -->
      <div class="drawer-header">
        <div class="header-left">
          <div class="icon-wrap icon-amber">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
          </div>
          <div>
            <h2 class="drawer-title">Field Maintenance & Work Orders (CMMS)</h2>
            <p class="drawer-subtitle">Automated SCADA Dispatch • Multimeter Diagnostic Checklists</p>
          </div>
        </div>
        <div class="header-right">
          <button @click="close" class="close-btn">&times;</button>
        </div>
      </div>

      <!-- Filter Tabs -->
      <div class="filter-tabs">
        <button 
          v-for="st in ['ALL', 'DISPATCHED', 'IN_PROGRESS', 'RESOLVED']" 
          :key="st" 
          @click="statusFilter = st; fetchWorkOrders()" 
          class="tab-btn" 
          :class="{ active: statusFilter === st }"
        >
          {{ st.replace('_', ' ') }}
        </button>
      </div>

      <!-- Work Orders List -->
      <div class="drawer-content">
        <div v-if="loading" class="loading-state">
          <span class="status-dot active"></span> Loading Work Orders from Laravel...
        </div>

        <div v-else-if="!workOrders.length" class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="text-emerald"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <span>No active work orders under filter "{{ statusFilter }}".</span>
        </div>

        <div v-else class="wo-list">
          <div 
            v-for="wo in workOrders" 
            :key="wo.id" 
            class="wo-card"
            :class="wo.priority === 'CRITICAL' ? 'card-critical' : ''"
          >
            <!-- Card Header -->
            <div class="wo-card-header">
              <div class="wo-meta-left">
                <span class="wo-id mono-val">{{ wo.id }}</span>
                <span class="badge" :class="wo.priority === 'CRITICAL' ? 'badge-rose' : 'badge-amber'">
                  {{ wo.priority }}
                </span>
                <span class="badge" :class="getStatusBadgeClass(wo.status)">
                  {{ wo.status }}
                </span>
              </div>
              <span class="wo-time mono-val">{{ formatDateTime(wo.dispatched_at) }}</span>
            </div>

            <!-- Title & Description -->
            <h4 class="wo-title">{{ wo.title }}</h4>
            <p class="wo-desc">{{ wo.description }}</p>

            <!-- Technician & GPS Info -->
            <div class="wo-details-grid">
              <div class="wo-detail-item">
                <span class="detail-label">Assigned Technician</span>
                <span class="detail-val">{{ wo.assigned_technician }}</span>
                <span class="detail-sub mono-val">{{ wo.technician_phone }}</span>
              </div>
              <div class="wo-detail-item">
                <span class="detail-label">Asset Location</span>
                <span class="detail-val mono-val">{{ wo.inverter_id }} <template v-if="wo.string_id">: {{ wo.string_id }}</template></span>
                <a :href="`https://maps.google.com/?q=${wo.gps_latitude},${wo.gps_longitude}`" target="_blank" class="detail-link mono-val">
                  📍 {{ wo.gps_latitude?.toFixed(4) }}°N, {{ Math.abs(wo.gps_longitude)?.toFixed(4) }}°W
                </a>
              </div>
            </div>

            <!-- Diagnostic Steps Checklist -->
            <div v-if="wo.diagnostic_steps && wo.diagnostic_steps.length" class="diagnostic-section">
              <span class="section-title">Multimeter Diagnostic Checklist:</span>
              <div class="steps-list">
                <label 
                  v-for="(step, sIdx) in wo.diagnostic_steps" 
                  :key="sIdx" 
                  class="step-item"
                  :class="{ completed: step.completed }"
                >
                  <input 
                    type="checkbox" 
                    :checked="step.completed" 
                    @change="toggleStep(wo, sIdx, $event.target.checked)"
                    :disabled="wo.status === 'RESOLVED'"
                  />
                  <span class="step-text">
                    <strong>Step {{ step.step }}:</strong> {{ step.task }}
                  </span>
                </label>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="wo-actions">
              <button 
                v-if="wo.status === 'DISPATCHED'" 
                @click="updateStatus(wo, 'IN_PROGRESS')" 
                class="btn-scada btn-scada-cyan"
              >
                Start Inspection
              </button>
              <button 
                v-if="wo.status === 'IN_PROGRESS'" 
                @click="updateStatus(wo, 'RESOLVED')" 
                class="btn-scada btn-scada-emerald"
              >
                Mark Ticket Resolved
              </button>
              <span v-if="wo.status === 'RESOLVED'" class="resolved-note text-emerald">
                ✓ Resolved at {{ formatDateTime(wo.resolved_at) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'updated'])

const workOrders = ref([])
const loading = ref(false)
const statusFilter = ref('ALL')

onMounted(() => {
  fetchWorkOrders()
})

watch(() => props.isOpen, (open) => {
  if (open) {
    fetchWorkOrders()
  }
})

async function fetchWorkOrders() {
  loading.value = true
  try {
    const url = statusFilter.value === 'ALL' ? '/api/v1/work-orders' : `/api/v1/work-orders?status=${statusFilter.value}`
    // Try Laravel backend on :8080 or relative proxy
    let res
    try {
      res = await fetch(`http://127.0.0.1:8080${url}`)
    } catch {
      res = await fetch(url)
    }
    const data = await res.json()
    workOrders.value = data || []
  } catch (err) {
    console.error('Error fetching work orders:', err)
  } finally {
    loading.value = false
  }
}

async function updateStatus(wo, newStatus) {
  try {
    const url = `http://127.0.0.1:8080/api/v1/work-orders/${wo.id}/status`
    await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
    wo.status = newStatus
    if (newStatus === 'RESOLVED') {
      wo.resolved_at = new Date().toISOString()
    }
    emit('updated')
  } catch (err) {
    console.error('Error updating status:', err)
  }
}

async function toggleStep(wo, stepIndex, isCompleted) {
  try {
    const url = `http://127.0.0.1:8080/api/v1/work-orders/${wo.id}/status`
    await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: wo.status === 'DISPATCHED' ? 'IN_PROGRESS' : wo.status,
        step_index: stepIndex,
        step_completed: isCompleted
      })
    })
    if (wo.diagnostic_steps && wo.diagnostic_steps[stepIndex]) {
      wo.diagnostic_steps[stepIndex].completed = isCompleted
    }
    if (wo.status === 'DISPATCHED') {
      wo.status = 'IN_PROGRESS'
    }
    emit('updated')
  } catch (err) {
    console.error('Error toggling step:', err)
  }
}

function getStatusBadgeClass(status) {
  if (status === 'RESOLVED') return 'badge-emerald'
  if (status === 'IN_PROGRESS') return 'badge-cyan'
  return 'badge-amber'
}

function formatDateTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleDateString() + ' ' + d.toTimeString().split(' ')[0]
  } catch {
    return isoStr
  }
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
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  z-index: 3000;
  display: flex;
  justify-content: flex-end;
}

.work-orders-drawer {
  width: 580px;
  max-width: 90vw;
  height: 100vh;
  background: #0d111a;
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.8);
  animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
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
.icon-amber { background: rgba(245, 158, 11, 0.12); }
.text-amber { color: var(--accent-amber); }
.text-emerald { color: var(--accent-emerald); }

.drawer-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
}

.drawer-subtitle {
  font-size: 0.75rem;
  color: var(--text-muted);
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

.filter-tabs {
  display: flex;
  padding: 10px 24px;
  gap: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  background: none;
  border: 1px solid transparent;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.tab-btn.active {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border-color);
  color: var(--text-primary);
}

.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 10px;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.wo-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wo-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wo-card.card-critical {
  border-color: rgba(244, 63, 94, 0.35);
  background: rgba(244, 63, 94, 0.03);
}

.wo-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.wo-meta-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wo-id {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

.wo-time {
  font-size: 0.72rem;
  color: var(--text-muted);
}

.wo-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.wo-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.wo-details-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  background: rgba(0, 0, 0, 0.25);
  padding: 10px 12px;
  border-radius: 6px;
}

.detail-label {
  font-size: 0.68rem;
  color: var(--text-muted);
  display: block;
}

.detail-val {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-sub {
  font-size: 0.7rem;
  color: var(--text-muted);
  display: block;
}

.detail-link {
  font-size: 0.72rem;
  color: var(--accent-cyan);
  text-decoration: none;
  display: block;
  margin-top: 2px;
}
.detail-link:hover { text-decoration: underline; }

.diagnostic-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-primary);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.78rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
}
.step-item:hover { background: rgba(255, 255, 255, 0.03); }
.step-item.completed {
  text-decoration: line-through;
  color: var(--text-muted);
}

.wo-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.btn-scada-emerald {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.4);
  color: var(--accent-emerald);
}
.btn-scada-emerald:hover {
  background: rgba(16, 185, 129, 0.25);
}

.resolved-note {
  font-size: 0.78rem;
  font-weight: 600;
}
</style>
