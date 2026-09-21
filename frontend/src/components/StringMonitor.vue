<template>
  <div class="glass-panel string-monitor-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-indigo">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-indigo"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 7h.01"/><path d="M17 7h.01"/><path d="M7 17h.01"/><path d="M17 17h.01"/></svg>
        </div>
        <div>
          <h3 class="card-title">Inverter String Voltage Divergence Matrix</h3>
          <p class="card-subtitle">32 PV String Channels • Real-time Shading & Fuse Fault Isolation</p>
        </div>
      </div>
      <div class="header-right">
        <span class="badge" :class="faultedStringsCount > 0 ? 'badge-rose' : 'badge-emerald'">
          {{ faultedStringsCount > 0 ? `${faultedStringsCount} String Faults Detected` : 'All 32 Strings Balanced' }}
        </span>
      </div>
    </div>

    <div class="inverters-grid">
      <div v-for="inv in inverters" :key="inv.inverter_id" class="inverter-block">
        <div class="inv-header">
          <span class="inv-id">{{ inv.inverter_id }}</span>
          <span class="inv-power mono-val">{{ inv.ac_power_kw }} kW</span>
          <span class="inv-temp mono-val" :class="{'text-rose': inv.inverter_temp_c >= 90}">{{ inv.inverter_temp_c }}°C</span>
        </div>

        <div class="strings-list">
          <div 
            v-for="s in inv.strings" 
            :key="s.string_id" 
            class="string-row" 
            :class="{
              'fault-blown': s.voltage_v < 100,
              'fault-shaded': s.voltage_v >= 100 && s.voltage_v < 700
            }"
          >
            <div class="string-meta">
              <span class="str-id mono-val">{{ s.string_id }}</span>
              <span v-if="s.voltage_v < 100" class="mini-tag tag-rose">FUSE BLOWN</span>
              <span v-else-if="s.voltage_v < 700" class="mini-tag tag-amber">SHADED</span>
            </div>

            <div class="str-values">
              <span class="mono-val str-volt">{{ s.voltage_v }}V</span>
              <span class="mono-val str-curr">{{ s.current_a }}A</span>
              <span class="mono-val str-pwr">{{ s.power_kw }} kW</span>
            </div>

            <!-- Voltage Bar -->
            <div class="volt-bar-bg">
              <div 
                class="volt-bar-fill" 
                :style="{ width: `${Math.min(100, (s.voltage_v / 900) * 100)}%` }"
                :class="s.voltage_v < 100 ? 'bar-rose' : (s.voltage_v < 700 ? 'bar-amber' : 'bar-emerald')"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  telemetry: {
    type: Object,
    default: () => ({})
  }
})

const inverters = computed(() => props.telemetry?.inverters || [])

const faultedStringsCount = computed(() => {
  let count = 0
  inverters.value.forEach(inv => {
    inv.strings?.forEach(s => {
      if (s.voltage_v < 700) count++
    })
  })
  return count
})
</script>

<style scoped>
.string-monitor-card {
  display: flex;
  flex-direction: column;
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
.icon-indigo { background: rgba(99, 102, 241, 0.1); }
.text-indigo { color: var(--accent-indigo); }

.card-title {
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.inverters-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 16px 20px;
}

.inverter-block {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
}

.inv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 6px;
}

.inv-id {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--text-primary);
}

.inv-power {
  font-size: 0.78rem;
  color: var(--accent-emerald);
}

.inv-temp {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.text-rose { color: var(--accent-rose); font-weight: 700; }

.strings-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.string-row {
  position: relative;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  padding: 6px 8px;
  overflow: hidden;
}

.string-row.fault-blown {
  background: rgba(244, 63, 94, 0.15);
  border-color: rgba(244, 63, 94, 0.4);
}

.string-row.fault-shaded {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.35);
}

.string-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.str-id {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.mini-tag {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}
.tag-rose { background: var(--accent-rose); color: #fff; }
.tag-amber { background: var(--accent-amber); color: #000; }

.str-values {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
  margin-bottom: 4px;
}

.str-volt { font-weight: 600; color: var(--text-primary); }
.str-curr { color: var(--text-secondary); }
.str-pwr { color: var(--accent-cyan); }

.volt-bar-bg {
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
  overflow: hidden;
}

.volt-bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}
.bar-emerald { background: var(--accent-emerald); }
.bar-amber { background: var(--accent-amber); }
.bar-rose { background: var(--accent-rose); }

@media (max-width: 1200px) {
  .inverters-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .inverters-grid {
    grid-template-columns: 1fr;
  }
}
</style>
