<template>
  <div class="glass-panel tariff-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap icon-emerald">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-emerald"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </div>
        <div>
          <h3 class="card-title">Dynamic Tariff & Economic Yield</h3>
          <p class="card-subtitle">Real-Time TOU Arbitrage & PPA Compliance</p>
        </div>
      </div>
      <div class="header-right">
        <span class="badge" :class="tariffTierClass">
          {{ tariffTierName }}
        </span>
      </div>
    </div>

    <div class="tariff-body">
      <div class="kpi-banner">
        <div class="kpi-main">
          <span class="kpi-sub">Current Grid Tariff</span>
          <span class="kpi-val mono-val">${{ tariffRate.toFixed(4) }} <small>/ kWh</small></span>
        </div>
        <div class="kpi-revenue">
          <span class="kpi-sub">Revenue Run-Rate</span>
          <span class="kpi-val mono-val text-emerald">${{ Math.round(revenueRate).toLocaleString() }} <small>/ hr</small></span>
        </div>
      </div>

      <!-- Tariff Schedule Timeline -->
      <div class="tariff-timeline-wrap">
        <div class="timeline-bar">
          <div class="tier-segment tier-offpeak" style="width: 29.1%"><span>Off-Peak ($0.06)</span></div>
          <div class="tier-segment tier-shoulder" style="width: 29.1%"><span>Shoulder ($0.14)</span></div>
          <div class="tier-segment tier-peak" style="width: 20.8%"><span>Peak ($0.32)</span></div>
          <div class="tier-segment tier-shoulder" style="width: 12.5%"><span>Shoulder</span></div>
          <div class="tier-segment tier-offpeak" style="width: 8.5%"><span>Off-Peak</span></div>
        </div>
        <div class="timeline-labels">
          <span>00:00</span>
          <span>07:00</span>
          <span>14:00</span>
          <span>19:00</span>
          <span>22:00</span>
          <span>24:00</span>
        </div>
      </div>

      <!-- Financial Summary Grid -->
      <div class="fin-summary-grid">
        <div class="fin-box">
          <span class="fin-label">Total Day Revenue</span>
          <span class="fin-num mono-val text-emerald">${{ Math.round(totalRevenue).toLocaleString() }}</span>
        </div>
        <div class="fin-box">
          <span class="fin-label">Avoided Penalties</span>
          <span class="fin-num mono-val text-cyan">${{ Math.round(totalSavings).toLocaleString() }}</span>
        </div>
        <div class="fin-box">
          <span class="fin-label">Accrued Penalties</span>
          <span class="fin-num mono-val text-rose">${{ Math.round(totalPenalties).toLocaleString() }}</span>
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

const tariffRate = computed(() => props.telemetry?.tariff_usd_kwh || 0.14)
const revenueRate = computed(() => props.telemetry?.bess_dispatch?.revenue_rate_usd_h || 0.0)
const totalRevenue = computed(() => props.telemetry?.financial_kpis?.total_revenue_usd || 0.0)
const totalSavings = computed(() => props.telemetry?.financial_kpis?.total_savings_usd || 0.0)
const totalPenalties = computed(() => props.telemetry?.financial_kpis?.total_penalties_usd || 0.0)

const tariffTierName = computed(() => {
  if (tariffRate.value >= 0.40) return 'CRITICAL SPIKE'
  if (tariffRate.value >= 0.28) return 'PEAK TARIFF'
  if (tariffRate.value >= 0.10) return 'SHOULDER TARIFF'
  return 'OFF-PEAK'
})

const tariffTierClass = computed(() => {
  if (tariffRate.value >= 0.40) return 'badge-rose'
  if (tariffRate.value >= 0.28) return 'badge-amber'
  if (tariffRate.value >= 0.10) return 'badge-cyan'
  return 'badge-emerald'
})
</script>

<style scoped>
.tariff-card {
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
.icon-emerald { background: rgba(16, 185, 129, 0.1); }
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

.tariff-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.kpi-banner {
  display: flex;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  padding: 14px 18px;
  border-radius: 8px;
}

.kpi-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 4px;
}

.kpi-val {
  font-size: 1.4rem;
  font-weight: 700;
}
.kpi-val small {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.tariff-timeline-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.timeline-bar {
  display: flex;
  height: 24px;
  border-radius: 6px;
  overflow: hidden;
  font-size: 0.65rem;
  font-weight: 600;
  text-align: center;
  line-height: 24px;
}

.tier-offpeak { background: #064e3b; color: #6ee7b7; }
.tier-shoulder { background: #0e7490; color: #a5f3fc; }
.tier-peak { background: #b45309; color: #fde68a; }

.timeline-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.fin-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.fin-box {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 10px 12px;
}

.fin-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 4px;
}

.fin-num {
  font-size: 1.1rem;
  font-weight: 700;
}

.text-cyan { color: var(--accent-cyan); }
.text-rose { color: var(--accent-rose); }
</style>
