<template>
  <div class="glass-panel plant-map-card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrap">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-emerald"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/><line x1="15" x2="15" y1="6" y2="21"/></svg>
        </div>
        <div>
          <h3 class="card-title">Geospatial Array & Inverter Topology</h3>
          <p class="card-subtitle">Mojave High-Desert Facility (34.924°N, 116.892°W) • 25.0 MW Nameplate</p>
        </div>
      </div>
      <div class="header-right">
        <span class="badge badge-emerald">
          <span class="status-dot active"></span>
          Telemetry 2s Synced
        </span>
      </div>
    </div>

    <!-- Leaflet Map Container -->
    <div class="map-wrapper">
      <div id="leaflet-map" class="map-container"></div>
      
      <!-- Overlaid Map Legend & Quick Stats -->
      <div class="map-overlay-legend">
        <div class="legend-item"><span class="legend-dot bg-emerald"></span> Inverters (4x 5MW)</div>
        <div class="legend-item"><span class="legend-dot bg-cyan"></span> Wind Turbines (2x 2.5MW)</div>
        <div class="legend-item"><span class="legend-dot bg-amber"></span> 10MWh BESS</div>
        <div class="legend-item"><span class="legend-dot bg-indigo"></span> Substation (230kV)</div>
      </div>

      <!-- Selected Inverter / Asset Inspector Drawer -->
      <div v-if="selectedAsset" class="asset-inspector-drawer glass-panel">
        <div class="drawer-header">
          <div>
            <span class="drawer-badge" :class="selectedAsset.status === 'FAULT' ? 'badge-rose' : (selectedAsset.status === 'WARNING' ? 'badge-amber' : 'badge-emerald')">
              {{ selectedAsset.status || 'ONLINE' }}
            </span>
            <h4 class="drawer-title">{{ selectedAsset.name || selectedAsset.inverter_id || selectedAsset.turbine_id }}</h4>
          </div>
          <button @click="selectedAsset = null" class="close-btn">&times;</button>
        </div>

        <div class="drawer-body">
          <div v-if="selectedAsset.strings" class="strings-grid">
            <div class="drawer-stat">
              <span class="stat-label">AC Power</span>
              <span class="stat-val mono-val">{{ selectedAsset.ac_power_kw }} kW</span>
            </div>
            <div class="drawer-stat">
              <span class="stat-label">IGBT Temp</span>
              <span class="stat-val mono-val" :class="{'text-rose': selectedAsset.inverter_temp_c >= 90}">
                {{ selectedAsset.inverter_temp_c }}°C
              </span>
            </div>
            <div class="drawer-stat">
              <span class="stat-label">DC Power</span>
              <span class="stat-val mono-val">{{ selectedAsset.dc_power_kw }} kW</span>
            </div>
            <div class="drawer-stat">
              <span class="stat-label">Strings Active</span>
              <span class="stat-val mono-val">{{ selectedAsset.strings.length }} / 8</span>
            </div>

            <!-- Mini String Voltage Matrix -->
            <div class="string-mini-list">
              <div v-for="s in selectedAsset.strings" :key="s.string_id" class="string-mini-item" :class="{'string-fault': s.voltage_v < 100}">
                <span class="mono-val text-muted">{{ s.string_id }}</span>
                <span class="mono-val">{{ s.voltage_v }}V</span>
                <span class="mono-val">{{ s.current_a }}A</span>
              </div>
            </div>
          </div>

          <div v-else-if="selectedAsset.turbine_id" class="turbine-details">
            <div class="drawer-stat">
              <span class="stat-label">Active Power</span>
              <span class="stat-val mono-val">{{ selectedAsset.power_kw }} kW</span>
            </div>
            <div class="drawer-stat">
              <span class="stat-label">Wind Speed</span>
              <span class="stat-val mono-val">{{ selectedAsset.wind_speed_ms }} m/s</span>
            </div>
            <div class="drawer-stat">
              <span class="stat-label">Rotor Speed</span>
              <span class="stat-val mono-val">{{ selectedAsset.rotor_rpm }} RPM</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch, ref } from 'vue'
import L from 'leaflet'

const props = defineProps({
  telemetry: {
    type: Object,
    default: () => ({})
  }
})

const selectedAsset = ref(null)
let map = null
let markers = {}

// Assets with coordinates centered around the Mojave site
const assetLocations = [
  { id: 'INV-01', name: 'Central Inverter INV-01', type: 'inverter', lat: 34.9255, lng: -116.8950 },
  { id: 'INV-02', name: 'Central Inverter INV-02', type: 'inverter', lat: 34.9242, lng: -116.8950 },
  { id: 'INV-03', name: 'Central Inverter INV-03', type: 'inverter', lat: 34.9255, lng: -116.8890 },
  { id: 'INV-04', name: 'Central Inverter INV-04', type: 'inverter', lat: 34.9242, lng: -116.8890 },
  { id: 'WTG-01', name: 'Wind Turbine WTG-01', type: 'turbine', lat: 34.9280, lng: -116.8920 },
  { id: 'WTG-02', name: 'Wind Turbine WTG-02', type: 'turbine', lat: 34.9215, lng: -116.8920 },
  { id: 'BESS-01', name: '10MWh BESS Storage Unit', type: 'bess', lat: 34.9248, lng: -116.8920 },
  { id: 'SUBSTATION-01', name: 'Interconnection Substation', type: 'substation', lat: 34.9230, lng: -116.8860 }
]

onMounted(() => {
  initMap()
})

watch(() => props.telemetry, (newTel) => {
  if (!newTel || !map) return
  updateMarkers(newTel)
}, { deep: true })

function initMap() {
  const container = document.getElementById('leaflet-map')
  if (!container) return

  map = L.map('leaflet-map', {
    center: [34.9245, -116.8915],
    zoom: 15,
    zoomControl: false,
    attributionControl: false
  })

  // CartoDB Dark Matter tiles
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(map)

  L.control.zoom({ position: 'topright' }).addTo(map)

  // Solar array boundary polygon
  const solarBoundary = [
    [34.9265, -116.8970],
    [34.9265, -116.8870],
    [34.9220, -116.8870],
    [34.9220, -116.8970]
  ]
  L.polygon(solarBoundary, {
    color: '#10b981',
    weight: 1.5,
    opacity: 0.4,
    fillColor: '#10b981',
    fillOpacity: 0.04,
    dashArray: '4, 8'
  }).addTo(map)

  // Add asset markers
  assetLocations.forEach(loc => {
    const el = document.createElement('div')
    el.className = `custom-map-node node-${loc.type}`
    el.innerHTML = `<div class="node-pulse"></div><div class="node-inner">${loc.id.split('-')[0]}</div>`
    
    const icon = L.divIcon({
      html: el,
      className: 'leaflet-custom-div-icon',
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    })

    const marker = L.marker([loc.lat, loc.lng], { icon }).addTo(map)
    marker.on('click', () => {
      findAndSelectAsset(loc)
    })
    markers[loc.id] = { marker, config: loc, el }
  })
}

function findAndSelectAsset(loc) {
  if (loc.type === 'inverter' && props.telemetry?.inverters) {
    const inv = props.telemetry.inverters.find(i => i.inverter_id === loc.id)
    if (inv) {
      selectedAsset.value = { ...inv, name: loc.name }
      return
    }
  } else if (loc.type === 'turbine' && props.telemetry?.turbines) {
    const turb = props.telemetry.turbines.find(t => t.turbine_id === loc.id)
    if (turb) {
      selectedAsset.value = { ...turb, name: loc.name }
      return
    }
  }
  selectedAsset.value = { ...loc, status: 'NORMAL' }
}

function updateMarkers(tel) {
  if (!tel.inverters) return

  tel.inverters.forEach(inv => {
    const m = markers[inv.inverter_id]
    if (m && m.el) {
      m.el.classList.remove('status-fault', 'status-warning', 'status-normal')
      if (inv.status === 'FAULT') {
        m.el.classList.add('status-fault')
      } else if (inv.status === 'WARNING') {
        m.el.classList.add('status-warning')
      } else {
        m.el.classList.add('status-normal')
      }
    }
  })

  // Update selected asset live values
  if (selectedAsset.value) {
    if (selectedAsset.value.inverter_id) {
      const updated = tel.inverters.find(i => i.inverter_id === selectedAsset.value.inverter_id)
      if (updated) selectedAsset.value = { ...selectedAsset.value, ...updated }
    } else if (selectedAsset.value.turbine_id && tel.turbines) {
      const updated = tel.turbines.find(t => t.turbine_id === selectedAsset.value.turbine_id)
      if (updated) selectedAsset.value = { ...selectedAsset.value, ...updated }
    }
  }
}
</script>

<style scoped>
.plant-map-card {
  display: flex;
  flex-direction: column;
  height: 480px;
  position: relative;
  overflow: hidden;
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
  background: rgba(16, 185, 129, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-title {
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.map-wrapper {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
}

.map-container {
  width: 100%;
  height: 100%;
  background: #080b11;
}

.map-overlay-legend {
  position: absolute;
  bottom: 14px;
  left: 14px;
  z-index: 1000;
  display: flex;
  gap: 14px;
  padding: 8px 14px;
  background: rgba(10, 14, 22, 0.85);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 0.75rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.bg-emerald { background-color: var(--accent-emerald); }
.bg-cyan { background-color: var(--accent-cyan); }
.bg-amber { background-color: var(--accent-amber); }
.bg-indigo { background-color: var(--accent-indigo); }

/* Asset Drawer */
.asset-inspector-drawer {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 290px;
  z-index: 1000;
  padding: 16px;
  box-shadow: 0 12px 36px rgba(0,0,0,0.6);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.drawer-badge {
  font-size: 0.68rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
  text-transform: uppercase;
}

.drawer-title {
  font-size: 0.9rem;
  font-weight: 600;
  margin-top: 4px;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
}
.close-btn:hover { color: var(--text-primary); }

.drawer-stat {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 0.8rem;
}
.stat-label { color: var(--text-muted); }
.stat-val { font-weight: 600; color: var(--text-primary); }
.text-rose { color: var(--accent-rose); }

.string-mini-list {
  margin-top: 10px;
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 4px;
}

.string-mini-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
  padding: 3px 6px;
  border-radius: 4px;
}
.string-mini-item:hover { background: rgba(255,255,255,0.05); }
.string-mini-item.string-fault {
  background: rgba(244, 63, 94, 0.2);
  color: var(--accent-rose);
  font-weight: 700;
}
</style>

<style>
/* Unscoped styles for Leaflet custom HTML markers */
.custom-map-node {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: pointer;
  transition: transform 0.2s ease;
}
.custom-map-node:hover { transform: scale(1.15); }

.node-inner {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 700;
  color: #fff;
  z-index: 2;
}

.node-inverter { background: #065f46; border: 2px solid #10b981; }
.node-turbine { background: #0e7490; border: 2px solid #06b6d4; }
.node-bess { background: #92400e; border: 2px solid #f59e0b; }
.node-substation { background: #3730a3; border: 2px solid #6366f1; }

.custom-map-node.status-fault {
  background: #9f1239 !important;
  border-color: #f43f5e !important;
  animation: pulse-node-fault 1.2s infinite;
}

@keyframes pulse-node-fault {
  0%, 100% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.7); }
  50% { box-shadow: 0 0 0 10px rgba(244, 63, 94, 0); }
}
</style>
