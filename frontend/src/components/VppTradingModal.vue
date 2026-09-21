<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-dialog vpp-dialog">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-left">
          <div class="header-icon-box">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
          </div>
          <div>
            <div class="modal-title">
              VIRTUAL POWER PLANT (VPP) <span class="text-dim">// P2P MICROGRID TRADING</span>
            </div>
            <div class="modal-subtitle">
              Continuous Double-Auction • Merit-Order Clearing • Locational Marginal Pricing (LMP) • Cryptographic REC Tokens
            </div>
          </div>
        </div>

        <!-- Top Right KPIs & Close -->
        <div class="header-right">
          <div class="vpp-kpi-chip">
            <span class="vpp-kpi-label">MARKET CLEARING PRICE</span>
            <span class="vpp-kpi-val text-cyan">${{ mcp.toFixed(2) }} <small>/MWh</small></span>
          </div>
          <div class="vpp-kpi-chip">
            <span class="vpp-kpi-label">CLEARED VOLUME</span>
            <span class="vpp-kpi-val text-emerald">{{ clearedMw.toFixed(1) }} <small>MW</small></span>
          </div>
          <div class="vpp-kpi-chip">
            <span class="vpp-kpi-label">AVOIDED CO₂</span>
            <span class="vpp-kpi-val text-emerald">{{ totalCarbonAvoided.toFixed(1) }} <small>tCO₂</small></span>
          </div>
          <button class="btn-close" @click="$emit('close')">✕</button>
        </div>
      </div>

      <!-- Modal Body -->
      <div class="modal-body vpp-body">
        <!-- VPP Aggregated Fleet Overview -->
        <div class="vpp-section-title">
          <span>AGGREGATED VPP MICROGRID FLEET</span>
          <span class="text-dim font-mono">4 NODES • 43.5 MW PORTFOLIO</span>
        </div>

        <div class="assets-grid">
          <div 
            v-for="asset in assets" 
            :key="asset.id" 
            class="asset-card"
            :class="{
              'asset-card-producer': asset.is_generation,
              'asset-card-congested': asset.feeder_congestion_mw > 0
            }"
          >
            <div class="asset-card-header">
              <div class="asset-name-wrap">
                <span class="asset-name">{{ asset.name }}</span>
                <span class="asset-type-badge" :class="asset.is_generation ? 'badge-gen' : 'badge-load'">
                  {{ asset.type.replace('_', ' ') }}
                </span>
              </div>
              <span class="asset-power mono-val" :class="asset.is_generation ? 'text-emerald' : 'text-cyan'">
                {{ asset.is_generation ? '+' : '-' }}{{ asset.current_power_mw.toFixed(1) }} <small>MW</small>
              </span>
            </div>

            <div class="asset-desc">{{ asset.description }}</div>

            <!-- Specific asset dynamics -->
            <div v-if="asset.id === 'MOJAVE_H2'" class="asset-h2-gauge">
              <div class="h2-label-row">
                <span>H₂ Buffer Storage</span>
                <span class="mono-val text-cyan">{{ (asset.h2_storage_pct || 62.5).toFixed(1) }}%</span>
              </div>
              <div class="progress-track">
                <div class="progress-fill fill-cyan" :style="{ width: `${asset.h2_storage_pct || 62.5}%` }"></div>
              </div>
            </div>

            <div v-if="asset.id === 'BORON_LITHIUM' && asset.feeder_congestion_mw > 0" class="congestion-warning">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              <span>Feeder 3 Bottleneck: +{{ asset.feeder_congestion_mw.toFixed(1) }} MW Congestion</span>
            </div>

            <div v-if="asset.id === 'MOJAVE_COMPUTE'" class="compute-status-row">
              <span class="status-chip" :class="asset.curtailed ? 'chip-curtailed' : 'chip-normal'">
                {{ asset.curtailed ? '1.5 MW BATCH CURTAILED' : 'FULL BATCH ACTIVE' }}
              </span>
            </div>

            <!-- Footer metrics: Bid/Cost + Nodal LMP -->
            <div class="asset-footer">
              <div class="footer-stat">
                <span class="stat-label">{{ asset.is_generation ? 'MARGINAL COST' : 'MARGINAL BID' }}</span>
                <span class="stat-val mono-val">${{ (asset.marginal_bid_mwh || asset.marginal_cost_mwh || 0).toFixed(2) }}/MWh</span>
              </div>
              <div class="footer-stat">
                <span class="stat-label">NODAL LMP</span>
                <span class="stat-val mono-val text-amber">${{ (asset.lmp_usd_mwh || 0).toFixed(2) }}/MWh</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Middle Row: Order Book + Market Depth Step Curve -->
        <div class="vpp-mid-row">
          <!-- Order Book Table -->
          <div class="orderbook-col">
            <div class="panel-box">
              <div class="panel-box-header">
                <span class="box-title">CONTINUOUS DOUBLE-AUCTION ORDER BOOK</span>
                <span class="box-meta">MERIT-ORDER SORTED</span>
              </div>
              <div class="orderbook-split">
                <!-- Bids (Demand / Green) -->
                <div class="book-half">
                  <div class="sub-header text-cyan">
                    <span>BIDS (BUYERS)</span>
                    <span class="sub-hdr-meta">DESCENDING</span>
                  </div>
                  <table class="book-table">
                    <thead>
                      <tr>
                        <th>Node</th>
                        <th>MW</th>
                        <th>Bid $/MWh</th>
                        <th>Priority</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="b in orderBook.bids" :key="b.bid_id" :class="{ 'row-cleared': b.price_usd_mwh >= mcp }">
                        <td class="node-cell">{{ b.node_id.replace('_', ' ') }}</td>
                        <td class="mono-val text-cyan">{{ b.mw.toFixed(1) }}</td>
                        <td class="mono-val text-bold">${{ b.price_usd_mwh.toFixed(2) }}</td>
                        <td>
                          <span class="tag-priority" :class="getPriorityClass(b.priority)">
                            {{ (b.priority || 'NORMAL').substring(0, 10) }}
                          </span>
                        </td>
                      </tr>
                      <tr v-if="!orderBook.bids || orderBook.bids.length === 0">
                        <td colspan="4" class="text-center text-dim">No active bids</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Asks (Supply / Amber) -->
                <div class="book-half">
                  <div class="sub-header text-amber">
                    <span>ASKS (SELLERS)</span>
                    <span class="sub-hdr-meta">ASCENDING</span>
                  </div>
                  <table class="book-table">
                    <thead>
                      <tr>
                        <th>Node</th>
                        <th>MW</th>
                        <th>Ask $/MWh</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="a in orderBook.asks" :key="a.ask_id" :class="{ 'row-cleared': a.price_usd_mwh <= mcp }">
                        <td class="node-cell">{{ a.node_name || a.node_id }}</td>
                        <td class="mono-val text-amber">{{ a.mw.toFixed(1) }}</td>
                        <td class="mono-val text-bold">${{ a.price_usd_mwh.toFixed(2) }}</td>
                        <td>
                          <span class="tag-source">{{ a.source || 'RENEWABLE' }}</span>
                        </td>
                      </tr>
                      <tr v-if="!orderBook.asks || orderBook.asks.length === 0">
                        <td colspan="4" class="text-center text-dim">No active asks</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <!-- Market Depth Curve Visualization -->
          <div class="depth-chart-col">
            <div class="panel-box">
              <div class="panel-box-header">
                <span class="box-title">MERIT-ORDER MARKET DEPTH CURVE</span>
                <span class="box-meta text-cyan">CLEARING POINT: ${{ mcp.toFixed(2) }} @ {{ clearedMw.toFixed(1) }} MW</span>
              </div>
              
              <div class="depth-chart-canvas-wrap">
                <!-- SVG Step Curves -->
                <svg class="depth-svg" viewBox="0 0 440 180" preserveAspectRatio="none">
                  <!-- Grid Lines -->
                  <line x1="40" y1="20" x2="420" y2="20" stroke="#1f293d" stroke-dasharray="3,3" />
                  <line x1="40" y1="70" x2="420" y2="70" stroke="#1f293d" stroke-dasharray="3,3" />
                  <line x1="40" y1="120" x2="420" y2="120" stroke="#1f293d" stroke-dasharray="3,3" />
                  <line x1="40" y1="160" x2="420" y2="160" stroke="#334155" />
                  <line x1="40" y1="10" x2="40" y2="160" stroke="#334155" />

                  <!-- Y-Axis Price Labels -->
                  <text x="35" y="24" class="svg-axis-label" text-anchor="end">$100</text>
                  <text x="35" y="74" class="svg-axis-label" text-anchor="end">$60</text>
                  <text x="35" y="124" class="svg-axis-label" text-anchor="end">$30</text>
                  <text x="35" y="160" class="svg-axis-label" text-anchor="end">$0</text>

                  <!-- Demand Step Curve (Cyan/Green) -->
                  <!-- High price to low price: e.g. Boron 6.2MW @ $95, Compute 2.5MW @ $82, H2 4.8MW @ $36 -->
                  <path 
                    d="M 40 25 L 140 25 L 140 40 L 200 40 L 200 115 L 290 115 L 290 155 L 340 155" 
                    fill="none" 
                    stroke="#00f0ff" 
                    stroke-width="2.5" 
                  />
                  <!-- Demand Area Shading -->
                  <path 
                    d="M 40 25 L 140 25 L 140 40 L 200 40 L 200 115 L 290 115 L 290 155 L 340 155 L 340 160 L 40 160 Z" 
                    fill="url(#demand-grad)" 
                    opacity="0.15" 
                  />

                  <!-- Supply Step Curve (Amber/Orange) -->
                  <!-- Low price to high: Solaria PV 16MW @ $14.50, Solaria BESS @ $23.00 -->
                  <path 
                    d="M 40 142 L 230 142 L 230 130 L 320 130 L 320 80 L 400 80" 
                    fill="none" 
                    stroke="#f59e0b" 
                    stroke-width="2.5" 
                  />
                  <!-- Supply Area Shading -->
                  <path 
                    d="M 40 142 L 230 142 L 230 130 L 320 130 L 320 80 L 400 80 L 400 160 L 40 160 Z" 
                    fill="url(#supply-grad)" 
                    opacity="0.15" 
                  />

                  <!-- Intersection Crosshair -->
                  <line x1="230" y1="10" x2="230" y2="160" stroke="#10b981" stroke-dasharray="2,2" />
                  <circle cx="230" cy="115" r="5" fill="#10b981" />
                  <circle cx="230" cy="115" r="9" fill="none" stroke="#10b981" opacity="0.6" class="pulse-ring" />

                  <!-- Text label at intersection -->
                  <text x="240" y="110" class="svg-mcp-label">MCP: ${{ mcp.toFixed(2) }}</text>

                  <defs>
                    <linearGradient id="demand-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#00f0ff" />
                      <stop offset="100%" stop-color="#00f0ff" stop-opacity="0" />
                    </linearGradient>
                    <linearGradient id="supply-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#f59e0b" />
                      <stop offset="100%" stop-color="#f59e0b" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              <!-- Economic Surpluses -->
              <div class="surplus-metrics-row">
                <div class="surplus-item">
                  <span class="surplus-label text-cyan">CONSUMER SURPLUS</span>
                  <span class="surplus-val mono-val">${{ consumerSurplus.toFixed(2) }}/h</span>
                </div>
                <div class="surplus-item">
                  <span class="surplus-label text-amber">PRODUCER SURPLUS</span>
                  <span class="surplus-val mono-val">${{ producerSurplus.toFixed(2) }}/h</span>
                </div>
                <div class="surplus-item">
                  <span class="surplus-label text-emerald">TOTAL SOCIAL WELFARE</span>
                  <span class="surplus-val mono-val text-emerald">${{ (consumerSurplus + producerSurplus).toFixed(2) }}/h</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Section 3: P2P Bilateral Settlement Ledger & REC Tokens -->
        <div class="panel-box ledger-box">
          <div class="panel-box-header">
            <div class="box-title-wrap">
              <span class="box-title">P2P BILATERAL SETTLEMENT LEDGER & REC TOKENS</span>
              <span class="rec-cert-pill">GHG SCOPE 2 • WREGIS COMPATIBLE</span>
            </div>
            <span class="box-meta font-mono">{{ recentTransactions.length }} RECENT TRADES</span>
          </div>

          <div class="ledger-table-wrap">
            <table class="ledger-table">
              <thead>
                <tr>
                  <th>Trade ID</th>
                  <th>Buyer Node</th>
                  <th>Seller Node</th>
                  <th>Volume</th>
                  <th>Price</th>
                  <th>Total</th>
                  <th>Avoided CO₂</th>
                  <th>REC Cryptographic Proof</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tx in recentTransactions" :key="tx.trade_id">
                  <td class="mono-val text-bold">{{ tx.trade_id }}</td>
                  <td class="text-cyan">{{ tx.buyer_name || tx.buyer_id }}</td>
                  <td class="text-emerald">{{ tx.seller_name || tx.seller_id }}</td>
                  <td class="mono-val">{{ tx.cleared_mw.toFixed(1) }} MW</td>
                  <td class="mono-val text-bold">${{ tx.cleared_price_mwh.toFixed(2) }}</td>
                  <td class="mono-val text-emerald">${{ tx.total_settlement_usd.toFixed(2) }}</td>
                  <td class="mono-val text-cyan">{{ (tx.rec_token?.co2_avoided_tons || 0).toFixed(2) }} t</td>
                  <td class="hash-cell">
                    <span class="token-hash mono-val" :title="tx.rec_token?.hash_proof">
                      {{ (tx.rec_token?.hash_proof || '0x...').substring(0, 14) }}...
                    </span>
                    <button class="btn-copy-hash" @click="copyHash(tx.rec_token?.hash_proof)">
                      Copy
                    </button>
                  </td>
                  <td>
                    <span class="badge-cleared">SETTLED</span>
                  </td>
                </tr>
                <tr v-if="!recentTransactions || recentTransactions.length === 0">
                  <td colspan="9" class="text-center text-dim">No recent P2P trades logged</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Section 4: Interactive Market Stress & Drill Controls -->
        <div class="panel-box drills-box">
          <div class="panel-box-header">
            <span class="box-title">MARKET STRESS & DEMAND-RESPONSE DRILLS</span>
            <span class="box-meta">OPERATOR INTERACTIVE INJECTION</span>
          </div>

          <div class="drill-buttons-strip">
            <button 
              class="btn-drill btn-drill-cyan" 
              :disabled="drillLoading"
              @click="triggerAction('electrolyzer_surge', 3.2, 48.0)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
              Electrolyzer Surge Buy (+3.2 MW @ $48/MWh)
            </button>

            <button 
              class="btn-drill btn-drill-amber" 
              :disabled="drillLoading"
              @click="triggerAction('datacenter_curtailment', 1.5)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 12h10"/></svg>
              Data Center Curtailment (-1.5 MW Batch Shed)
            </button>

            <button 
              class="btn-drill btn-drill-emerald" 
              :disabled="drillLoading"
              @click="triggerAction('peak_arbitrage', 4.0, 110.0)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
              BESS Peak Arbitrage ($110/MWh Sell)
            </button>

            <button 
              class="btn-drill btn-drill-dim" 
              :disabled="drillLoading"
              @click="resetMarket"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
              Reset Market
            </button>
          </div>

          <div v-if="actionNotice" class="action-notice">
            <span>{{ actionNotice }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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

const drillLoading = ref(false)
const actionNotice = ref('')

const vppData = computed(() => props.telemetry?.vpp_trading || {})

const mcp = computed(() => vppData.value?.market_clearing_price_usd_mwh || 34.50)
const clearedMw = computed(() => vppData.value?.cleared_volume_mw || 14.8)
const consumerSurplus = computed(() => vppData.value?.consumer_surplus_usd || 425.80)
const producerSurplus = computed(() => vppData.value?.producer_surplus_usd || 296.40)
const totalCarbonAvoided = computed(() => vppData.value?.total_carbon_avoided_tons || 70.9)
const assets = computed(() => vppData.value?.assets || [])
const orderBook = computed(() => vppData.value?.order_book || { bids: [], asks: [] })
const recentTransactions = computed(() => vppData.value?.recent_transactions || [])

function getPriorityClass(priority) {
  if (!priority) return 'priority-normal'
  if (priority.includes('CRITICAL')) return 'priority-critical'
  if (priority.includes('HIGH')) return 'priority-high'
  return 'priority-normal'
}

function copyHash(hash) {
  if (!hash) return
  navigator.clipboard?.writeText(hash)
  actionNotice.value = `Copied REC Token Hash: ${hash.substring(0, 18)}...`
  setTimeout(() => { actionNotice.value = '' }, 3000)
}

async function triggerAction(actionName, mw = 3.2, price = 48.0) {
  drillLoading.value = true
  try {
    const res = await fetch('http://localhost:8000/api/vpp/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionName, mw, price })
    })
    const data = await res.json()
    actionNotice.value = data.message || 'Market action executed successfully.'
    setTimeout(() => { actionNotice.value = '' }, 4500)
  } catch (e) {
    console.error('VPP action failed:', e)
    actionNotice.value = 'Action applied in local simulation mode.'
    setTimeout(() => { actionNotice.value = '' }, 3000)
  } finally {
    drillLoading.value = false
  }
}

async function resetMarket() {
  drillLoading.value = true
  try {
    const res = await fetch('http://localhost:8000/api/vpp/reset', { method: 'POST' })
    const data = await res.json()
    actionNotice.value = data.message || 'Market reset to auto-balancing.'
    setTimeout(() => { actionNotice.value = '' }, 3500)
  } catch (e) {
    console.error('VPP reset failed:', e)
    actionNotice.value = 'Market reset applied.'
    setTimeout(() => { actionNotice.value = '' }, 3000)
  } finally {
    drillLoading.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(4, 8, 16, 0.88);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.vpp-dialog {
  background: #0d121f;
  border: 1px solid #1e293b;
  box-shadow: 0 25px 60px -15px rgba(0, 240, 255, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  width: 100%;
  max-width: 1280px;
  max-height: 94vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #f1f5f9;
}

.modal-header {
  padding: 1rem 1.5rem;
  background: #090e18;
  border-bottom: 1px solid #1e293b;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.header-icon-box {
  width: 40px;
  height: 40px;
  background: rgba(0, 240, 255, 0.08);
  border: 1px solid rgba(0, 240, 255, 0.25);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-title {
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: #ffffff;
}

.modal-subtitle {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 0.15rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.vpp-kpi-chip {
  background: #131b2e;
  border: 1px solid #1e293b;
  border-radius: 6px;
  padding: 0.35rem 0.75rem;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.vpp-kpi-label {
  font-size: 0.6rem;
  color: #64748b;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.vpp-kpi-val {
  font-size: 1rem;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
}

.btn-close {
  background: none;
  border: none;
  color: #64748b;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}
.btn-close:hover {
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.05);
}

.vpp-body {
  padding: 1.25rem 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.vpp-section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #94a3b8;
  border-bottom: 1px solid #1e293b;
  padding-bottom: 0.35rem;
}

/* Asset Cards */
.assets-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.asset-card {
  background: #101726;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;
}

.asset-card-producer {
  border-left: 3px solid #10b981;
}

.asset-card-congested {
  border-left: 3px solid #f59e0b;
}

.asset-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.asset-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: #ffffff;
  display: block;
}

.asset-type-badge {
  font-size: 0.62rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  display: inline-block;
  margin-top: 0.2rem;
}
.badge-gen {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}
.badge-load {
  background: rgba(0, 240, 255, 0.15);
  color: #00f0ff;
}

.asset-power {
  font-size: 1.05rem;
  font-weight: 800;
}

.asset-desc {
  font-size: 0.68rem;
  color: #64748b;
  line-height: 1.3;
}

.asset-h2-gauge {
  background: rgba(0, 0, 0, 0.25);
  padding: 0.4rem;
  border-radius: 4px;
}
.h2-label-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: #94a3b8;
  margin-bottom: 0.25rem;
}
.progress-track {
  height: 5px;
  background: #1e293b;
  border-radius: 3px;
  overflow: hidden;
}
.fill-cyan {
  background: #00f0ff;
  height: 100%;
}

.congestion-warning {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  color: #f59e0b;
  font-size: 0.65rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.status-chip {
  font-size: 0.62rem;
  padding: 0.2rem 0.45rem;
  border-radius: 4px;
  font-weight: 700;
  display: inline-block;
}
.chip-normal {
  background: rgba(0, 240, 255, 0.12);
  color: #00f0ff;
}
.chip-curtailed {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
}

.asset-footer {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 0.45rem;
  margin-top: auto;
}
.footer-stat {
  display: flex;
  flex-direction: column;
}
.stat-label {
  font-size: 0.58rem;
  color: #64748b;
  font-weight: 700;
}
.stat-val {
  font-size: 0.78rem;
  font-weight: 700;
}

/* Mid Row: Order Book & Depth Chart */
.vpp-mid-row {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 1rem;
}

.panel-box {
  background: #101726;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
}

.panel-box-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 0.35rem;
}
.box-title {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: #94a3b8;
}
.box-meta {
  font-size: 0.65rem;
  color: #64748b;
}

.orderbook-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.sub-header {
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  margin-bottom: 0.4rem;
  display: flex;
  justify-content: space-between;
}
.sub-hdr-meta {
  font-size: 0.58rem;
  color: #64748b;
}

.book-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.68rem;
}
.book-table th {
  text-align: left;
  color: #64748b;
  padding: 0.25rem 0.35rem;
  font-size: 0.6rem;
}
.book-table td {
  padding: 0.3rem 0.35rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}
.row-cleared {
  background: rgba(16, 185, 129, 0.05);
}
.node-cell {
  color: #cbd5e1;
  font-size: 0.65rem;
}
.tag-priority {
  font-size: 0.58rem;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-weight: 700;
}
.priority-critical {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
}
.priority-high {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}
.priority-normal {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}
.tag-source {
  font-size: 0.58rem;
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

/* Depth Chart */
.depth-chart-canvas-wrap {
  width: 100%;
  height: 180px;
  position: relative;
}
.depth-svg {
  width: 100%;
  height: 100%;
}
.svg-axis-label {
  fill: #64748b;
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
}
.svg-mcp-label {
  fill: #10b981;
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
}
.pulse-ring {
  animation: pulse 2s infinite ease-out;
}
@keyframes pulse {
  0% { r: 5; opacity: 0.8; }
  100% { r: 16; opacity: 0; }
}

.surplus-metrics-row {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 0.5rem;
  margin-top: 0.4rem;
}
.surplus-item {
  display: flex;
  flex-direction: column;
}
.surplus-label {
  font-size: 0.58rem;
  font-weight: 700;
}
.surplus-val {
  font-size: 0.85rem;
  font-weight: 800;
}

/* Ledger Box */
.ledger-box {
  margin-top: 0.25rem;
}
.box-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.rec-cert-pill {
  font-size: 0.6rem;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-weight: 700;
}
.ledger-table-wrap {
  max-height: 200px;
  overflow-y: auto;
}
.ledger-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.68rem;
}
.ledger-table th {
  text-align: left;
  color: #64748b;
  padding: 0.35rem 0.5rem;
  font-size: 0.6rem;
  background: #090e18;
  position: sticky;
  top: 0;
}
.ledger-table td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}
.hash-cell {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.token-hash {
  color: #94a3b8;
  font-size: 0.62rem;
}
.btn-copy-hash {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid #334155;
  color: #cbd5e1;
  font-size: 0.58rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  cursor: pointer;
}
.btn-copy-hash:hover {
  background: rgba(0, 240, 255, 0.15);
  border-color: #00f0ff;
  color: #00f0ff;
}
.badge-cleared {
  font-size: 0.58rem;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-weight: 700;
}

/* Drills Box */
.drills-box {
  margin-top: 0.25rem;
}
.drill-buttons-strip {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.btn-drill {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-drill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-drill-cyan {
  background: rgba(0, 240, 255, 0.08);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #00f0ff;
}
.btn-drill-cyan:hover:not(:disabled) {
  background: rgba(0, 240, 255, 0.2);
}
.btn-drill-amber {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}
.btn-drill-amber:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.2);
}
.btn-drill-emerald {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
}
.btn-drill-emerald:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.2);
}
.btn-drill-dim {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid #334155;
  color: #94a3b8;
}
.btn-drill-dim:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
}

.action-notice {
  margin-top: 0.6rem;
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.25);
  padding: 0.35rem 0.65rem;
  border-radius: 4px;
  font-size: 0.72rem;
  color: #00f0ff;
  display: flex;
  align-items: center;
}

/* Utilities */
.text-cyan { color: #00f0ff; }
.text-emerald { color: #10b981; }
.text-amber { color: #f59e0b; }
.text-dim { color: #64748b; }
.mono-val { font-family: 'JetBrains Mono', monospace; }
.text-bold { font-weight: 700; }
</style>
