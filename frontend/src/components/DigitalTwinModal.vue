<template>
  <div class="twin-modal-backdrop" @keydown.esc="close" tabindex="0">
    <div class="twin-modal-container">
      <!-- 3D SCADA Top Navigation Bar -->
      <div class="twin-header">
        <div class="twin-brand">
          <div class="twin-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
          </div>
          <div>
            <div class="twin-title">
              SOLARIA WEST <span class="twin-sub">// 3D DIGITAL TWIN & REAL-TIME TRACKER</span>
            </div>
            <div class="twin-loc">
              34.924° N, 116.892° W • Mojave Desert • Single-Axis N-S Horiz Tracker (GCR: 0.40)
            </div>
          </div>
        </div>

        <!-- Live Sun & Tracker Telemetry Badges -->
        <div class="twin-telemetry-strip">
          <div class="twin-badge">
            <span class="tb-label">SUN ELEVATION</span>
            <span class="tb-val mono-val text-amber">{{ sunElevation.toFixed(1) }}°</span>
          </div>
          <div class="twin-badge">
            <span class="tb-label">SUN AZIMUTH</span>
            <span class="tb-val mono-val text-amber">{{ sunAzimuth.toFixed(1) }}°</span>
          </div>
          <div class="twin-badge">
            <span class="tb-label">TRACKER TILT</span>
            <span class="tb-val mono-val text-cyan">{{ currentTilt.toFixed(1) }}°</span>
          </div>
          <div class="twin-badge">
            <span class="tb-label">TRACKER MODE</span>
            <span class="tb-status-pill" :class="trackerModeClass">{{ trackerMode }}</span>
          </div>
          <div class="twin-badge">
            <span class="tb-label">WIND TURBINES</span>
            <span class="tb-val mono-val text-emerald">{{ (telemetry?.turbines?.[0]?.rotor_rpm || 0).toFixed(1) }} <small>RPM</small></span>
          </div>
        </div>

        <!-- Visual Mode & Camera Controls -->
        <div class="twin-controls-wrap">
          <!-- Visual Modes -->
          <div class="mode-selector">
            <button 
              @click="visualMode = 'PBR'" 
              class="mode-btn" 
              :class="{ active: visualMode === 'PBR' }"
              title="Standard Photorealistic Industrial Shading"
            >
              Photoreal
            </button>
            <button 
              @click="visualMode = 'THERMAL'" 
              class="mode-btn mode-btn-thermal" 
              :class="{ active: visualMode === 'THERMAL' }"
              title="Thermal Infrared False-Color Temperature Heatmap"
            >
              Thermal IR
            </button>
            <button 
              @click="visualMode = 'FAULTS'" 
              class="mode-btn mode-btn-fault" 
              :class="{ active: visualMode === 'FAULTS' }"
              title="String Electrical Fault Highlighting"
            >
              Fault View
            </button>
          </div>

          <!-- Close Modal -->
          <button @click="close" class="twin-close-btn" title="Exit 3D View (ESC)">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>

      <!-- 3D Canvas Viewport & Floating HUD -->
      <div class="twin-canvas-wrapper" ref="canvasContainer">
        <!-- Canvas renders here -->

        <!-- Camera Preset Floating Toolbar -->
        <div class="camera-toolbar">
          <span class="cam-label">CAMERA:</span>
          <button @click="setCameraPreset('overview')" :class="{ active: activePreset === 'overview' }">Full Plant</button>
          <button @click="setCameraPreset('solar')" :class="{ active: activePreset === 'solar' }">Solar Arrays</button>
          <button @click="setCameraPreset('wind')" :class="{ active: activePreset === 'wind' }">Wind Turbines</button>
          <button @click="setCameraPreset('bess')" :class="{ active: activePreset === 'bess' }">BESS Megapack</button>
          <button @click="setCameraPreset('substation')" :class="{ active: activePreset === 'substation' }">Substation</button>
        </div>

        <!-- Manual Tracker Override Overlay -->
        <div class="tracker-override-card">
          <div class="override-header">
            <span>MOTORIZED TRACKER OVERRIDE</span>
            <button 
              @click="manualOverride = !manualOverride" 
              class="override-toggle"
              :class="{ active: manualOverride }"
            >
              {{ manualOverride ? 'MANUAL' : 'AUTO' }}
            </button>
          </div>
          <div v-if="manualOverride" class="override-slider-wrap">
            <div class="slider-labels">
              <span>-60° (East)</span>
              <span class="text-cyan mono-val">{{ manualTilt.toFixed(1) }}°</span>
              <span>+60° (West)</span>
            </div>
            <input 
              type="range" 
              min="-60" 
              max="60" 
              step="0.5" 
              v-model.number="manualTilt" 
              class="scada-range"
            />
          </div>
          <div v-else class="override-info">
            Tracking Sun: <span class="text-cyan">{{ trackerMode }}</span> at 
            <span class="text-emerald mono-val">{{ currentTilt.toFixed(1) }}°</span>
          </div>
        </div>

        <!-- Raycasting SCADA Asset HUD -->
        <div v-if="inspectedAsset" class="asset-hud-card" :style="hudPositionStyle">
          <div class="asset-hud-header">
            <span class="asset-type-tag">{{ inspectedAsset.type }}</span>
            <span class="asset-id">{{ inspectedAsset.id }}</span>
            <button @click="inspectedAsset = null" class="hud-close">&times;</button>
          </div>
          <div class="asset-hud-body">
            <div v-for="(val, label) in inspectedAsset.metrics" :key="label" class="hud-row">
              <span class="hud-label">{{ label }}</span>
              <span class="hud-val mono-val">{{ val }}</span>
            </div>
            <div v-if="inspectedAsset.fault" class="hud-alert-banner">
              ⚠️ {{ inspectedAsset.fault }}
            </div>
          </div>
        </div>

        <!-- Legend Bar (Thermal / Photoreal) -->
        <div class="twin-legend">
          <div v-if="visualMode === 'THERMAL'" class="thermal-legend">
            <span class="leg-label">TEMP (°C):</span>
            <span class="leg-stop" style="color: #3b82f6;">25°</span>
            <div class="thermal-bar"></div>
            <span class="leg-stop" style="color: #ef4444;">85°+</span>
          </div>
          <div v-else-if="visualMode === 'FAULTS'" class="fault-legend">
            <span class="dot-normal"></span> Normal Operation
            <span class="dot-fault"></span> Blown Fuse / Inverter Alarm
          </div>
          <div v-else class="pbr-legend">
            <span>Left-Click: Orbit • Right-Click: Pan • Scroll: Zoom</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const props = defineProps({
  telemetry: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

const canvasContainer = ref(null)
const visualMode = ref('PBR') // 'PBR' | 'THERMAL' | 'FAULTS'
const activePreset = ref('overview')
const manualOverride = ref(false)
const manualTilt = ref(0.0)
const inspectedAsset = ref(null)
const hudPositionStyle = ref({ top: '80px', right: '30px' })

// Telemetry computed values
const sunElevation = computed(() => props.telemetry?.spatial_tracking?.sun_elevation_deg ?? 48.0)
const sunAzimuth = computed(() => props.telemetry?.spatial_tracking?.sun_azimuth_deg ?? 194.0)
const autoTilt = computed(() => props.telemetry?.spatial_tracking?.tracker_tilt_deg ?? 18.0)
const trackerMode = computed(() => {
  if (manualOverride.value) return 'MANUAL_OVERRIDE'
  return props.telemetry?.spatial_tracking?.tracker_mode ?? 'TRUE_TRACKING'
})

const currentTilt = computed(() => {
  if (manualOverride.value) return manualTilt.value
  return autoTilt.value
})

const trackerModeClass = computed(() => {
  if (trackerMode.value === 'BACKTRACKING') return 'pill-amber'
  if (trackerMode.value === 'MANUAL_OVERRIDE') return 'pill-purple'
  if (trackerMode.value === 'NIGHT_STOW') return 'pill-slate'
  return 'pill-emerald'
})

// Three.js instances
let scene, camera, renderer, controls, animationFrameId
let dirSunLight, ambientLight
let trackerRowGroups = [] // 32 rows of PV tables
let turbineRotors = []    // Wind turbine rotor meshes
let bessContainers = []   // BESS container meshes
let inverterSkids = []    // Inverter stations
let clickableObjects = [] // For raycasting
let raycaster, mousePointer

// Materials cache
let pbrPanelMaterial, thermalMaterial, faultMaterial
let pbrFrameMaterial, groundMaterial

function initThree() {
  if (!canvasContainer.value) return
  const width = canvasContainer.value.clientWidth
  const height = canvasContainer.value.clientHeight

  // 1. Scene
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a101d)
  scene.fog = new THREE.FogExp2(0x0a101d, 0.0035)

  // 2. Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 1000)
  camera.position.set(0, 75, 130)

  // 3. Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.15
  canvasContainer.value.appendChild(renderer.domElement)

  // 4. Controls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.maxPolarAngle = Math.PI / 2 - 0.02 // Don't dip below ground
  controls.minDistance = 10
  controls.maxDistance = 350
  controls.target.set(0, 5, 0)

  // 5. Lighting
  ambientLight = new THREE.AmbientLight(0xd4e2ff, 0.6)
  scene.add(ambientLight)

  dirSunLight = new THREE.DirectionalLight(0xfffaed, 2.2)
  dirSunLight.castShadow = true
  dirSunLight.shadow.mapSize.width = 2048
  dirSunLight.shadow.mapSize.height = 2048
  dirSunLight.shadow.camera.near = 10
  dirSunLight.shadow.camera.far = 300
  dirSunLight.shadow.camera.left = -100
  dirSunLight.shadow.camera.right = 100
  dirSunLight.shadow.camera.top = 100
  dirSunLight.shadow.camera.bottom = -100
  dirSunLight.shadow.bias = -0.0005
  scene.add(dirSunLight)

  // 6. Materials
  initMaterials()

  // 7. Build 3D Plant Layout
  buildTerrain()
  buildSolarArrays()
  buildWindTurbines()
  buildBessFacility()
  buildSubstation()

  // 8. Raycaster setup
  raycaster = new THREE.Raycaster()
  mousePointer = new THREE.Vector2()
  renderer.domElement.addEventListener('click', onCanvasClick)
  window.addEventListener('resize', onWindowResize)

  // 9. Initial positioning
  updateSunPosition()
  updateTrackerTilt(currentTilt.value)

  // 10. Animation Loop
  animate()
}

function initMaterials() {
  // Photorealistic PV Panel Glass (Navy-blue anti-reflective coating)
  pbrPanelMaterial = new THREE.MeshStandardMaterial({
    color: 0x0a1c36,
    metalness: 0.85,
    roughness: 0.25,
    envMapIntensity: 1.0
  })

  // Aluminum Frame & Torque Tube
  pbrFrameMaterial = new THREE.MeshStandardMaterial({
    color: 0x718096,
    metalness: 0.7,
    roughness: 0.4
  })

  // Thermal False-Color Material (Default warm green-yellow ~48°C)
  thermalMaterial = new THREE.MeshStandardMaterial({
    color: 0x10b981,
    roughness: 0.5,
    metalness: 0.1
  })

  // Fault Material (Pulsing high-vis neon red)
  faultMaterial = new THREE.MeshStandardMaterial({
    color: 0xef4444,
    emissive: 0xef4444,
    emissiveIntensity: 0.8,
    roughness: 0.2
  })
}

function buildTerrain() {
  // High-desert sand terrain
  const groundGeo = new THREE.PlaneGeometry(350, 350, 32, 32)
  groundMaterial = new THREE.MeshStandardMaterial({
    color: 0x1a2332,
    roughness: 0.9,
    metalness: 0.1
  })
  const ground = new THREE.Mesh(groundGeo, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)

  // Cyber SCADA Grid overlay
  const gridHelper = new THREE.GridHelper(300, 60, 0x10b981, 0x1e293b)
  gridHelper.position.y = 0.05
  scene.add(gridHelper)

  // Cardinal Compass Markers
  createCompassMarker('N (North)', new THREE.Vector3(0, 0.2, -145), 0x06b6d4)
  createCompassMarker('S (South)', new THREE.Vector3(0, 0.2, 145), 0x64748b)
  createCompassMarker('E (East)', new THREE.Vector3(145, 0.2, 0), 0xf59e0b)
  createCompassMarker('W (West)', new THREE.Vector3(-145, 0.2, 0), 0xf59e0b)
}

function createCompassMarker(text, position, colorHex) {
  // Simple post marker
  const markerGeo = new THREE.CylinderGeometry(0.5, 0.5, 2, 8)
  const markerMat = new THREE.MeshBasicMaterial({ color: colorHex })
  const marker = new THREE.Mesh(markerGeo, markerMat)
  marker.position.copy(position)
  scene.add(marker)
}

function buildSolarArrays() {
  // 4 Inverter Zones: INV-01, INV-02, INV-03, INV-04
  // Each zone contains 8 single-axis tracker rows (N-S axis)
  const zoneOffsets = [
    { id: 'INV-01', x: -60, z: -40 },
    { id: 'INV-02', x: 40, z: -40 },
    { id: 'INV-03', x: -60, z: 40 },
    { id: 'INV-04', x: 40, z: 40 }
  ]

  const rowLength = 28 // 28m long torque tube
  const rowPitch = 7   // 7m pitch between rows (GCR = 2.8 / 7 = 0.40)

  zoneOffsets.forEach((zone, zoneIdx) => {
    // Inverter Concrete Skid
    const skidGeo = new THREE.BoxGeometry(4, 2.5, 5)
    const skidMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.5, roughness: 0.4 })
    const skid = new THREE.Mesh(skidGeo, skidMat)
    skid.position.set(zone.x + 15, 1.25, zone.z + 10)
    skid.castShadow = true
    skid.receiveShadow = true
    skid.userData = {
      type: 'INVERTER',
      id: zone.id,
      zoneIndex: zoneIdx
    }
    scene.add(skid)
    inverterSkids.push(skid)
    clickableObjects.push(skid)

    // Skid Indicator LED
    const ledGeo = new THREE.SphereGeometry(0.2, 8, 8)
    const ledMat = new THREE.MeshBasicMaterial({ color: 0x10b981 })
    const led = new THREE.Mesh(ledGeo, ledMat)
    led.position.set(zone.x + 15, 2.7, zone.z + 10)
    scene.add(led)

    // 8 Single-Axis Rows per Inverter
    for (let r = 0; r < 8; r++) {
      const rowX = zone.x + (r * rowPitch) - 20
      const rowZ = zone.z

      // Row Group (Rotates along Z axis for N-S tracker tube)
      const rowGroup = new THREE.Group()
      rowGroup.position.set(rowX, 2.2, rowZ)

      // Piers (support posts anchored to ground)
      const pierGeo = new THREE.CylinderGeometry(0.12, 0.15, 2.2, 8)
      for (let p = -12; p <= 12; p += 6) {
        const pier = new THREE.Mesh(pierGeo, pbrFrameMaterial)
        pier.position.set(0, -1.1, p)
        pier.castShadow = true
        rowGroup.add(pier)
      }

      // Rotating Tracker Sub-Group
      const trackerTable = new THREE.Group()

      // Central Steel Torque Tube (along Z-axis)
      const tubeGeo = new THREE.CylinderGeometry(0.18, 0.18, rowLength, 12)
      const tube = new THREE.Mesh(tubeGeo, pbrFrameMaterial)
      tube.rotation.x = Math.PI / 2
      tube.castShadow = true
      trackerTable.add(tube)

      // PV Panel Tables mounted on torque tube
      const panelTableGeo = new THREE.BoxGeometry(2.6, 0.08, rowLength - 1)
      const panelMesh = new THREE.Mesh(panelTableGeo, pbrPanelMaterial)
      panelMesh.castShadow = true
      panelMesh.receiveShadow = true
      panelMesh.userData = {
        type: 'STRING_TABLE',
        id: `${zone.id}:STR-${String(r + 1).padStart(2, '0')}`,
        inverterId: zone.id,
        stringIndex: r
      }
      trackerTable.add(panelMesh)
      clickableObjects.push(panelMesh)

      rowGroup.add(trackerTable)
      scene.add(rowGroup)

      trackerRowGroups.push({
        group: trackerTable,
        mesh: panelMesh,
        inverterId: zone.id,
        stringId: `STR-${String(r + 1).padStart(2, '0')}`,
        stringIndex: r
      })
    }
  })
}

function buildWindTurbines() {
  // 2x 2.5 MW Wind Turbines (WTG-01 & WTG-02) located north of the solar field
  const turbinePositions = [
    { id: 'WTG-01', x: -45, z: -100 },
    { id: 'WTG-02', x: 45, z: -100 }
  ]

  const towerHeight = 35 // Scaled 35m tower
  const bladeLength = 18

  turbinePositions.forEach((wtg) => {
    const turbineGroup = new THREE.Group()
    turbineGroup.position.set(wtg.x, 0, wtg.z)

    // Tower (Tapered steel tube)
    const towerGeo = new THREE.CylinderGeometry(1.0, 1.8, towerHeight, 16)
    const towerMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.3, metalness: 0.4 })
    const tower = new THREE.Mesh(towerGeo, towerMat)
    tower.position.y = towerHeight / 2
    tower.castShadow = true
    tower.receiveShadow = true
    tower.userData = { type: 'TURBINE', id: wtg.id }
    turbineGroup.add(tower)
    clickableObjects.push(tower)

    // Nacelle (Rotates to wind yaw)
    const nacelleGeo = new THREE.BoxGeometry(3.5, 2.5, 6)
    const nacelleMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.3, metalness: 0.4 })
    const nacelle = new THREE.Mesh(nacelleGeo, nacelleMat)
    nacelle.position.set(0, towerHeight, 0)
    nacelle.castShadow = true
    nacelle.userData = { type: 'TURBINE', id: wtg.id }
    turbineGroup.add(nacelle)
    clickableObjects.push(nacelle)

    // Rotor Hub & 3 Blades
    const rotorGroup = new THREE.Group()
    rotorGroup.position.set(0, towerHeight, 3.2) // Front of nacelle

    // Hub
    const hubGeo = new THREE.SphereGeometry(1.2, 12, 12)
    const hubMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.4 })
    const hub = new THREE.Mesh(hubGeo, hubMat)
    rotorGroup.add(hub)

    // 3 Aerodynamic Blades
    const bladeGeo = new THREE.ConeGeometry(0.7, bladeLength, 8)
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.2 })

    for (let b = 0; b < 3; b++) {
      const bladeMesh = new THREE.Mesh(bladeGeo, bladeMat)
      bladeMesh.position.y = bladeLength / 2 + 0.8
      bladeMesh.castShadow = true

      const bladeHolder = new THREE.Group()
      bladeHolder.rotation.z = (b * 2 * Math.PI) / 3
      bladeHolder.add(bladeMesh)
      rotorGroup.add(bladeHolder)
    }

    turbineGroup.add(rotorGroup)
    scene.add(turbineGroup)

    turbineRotors.push({
      rotor: rotorGroup,
      id: wtg.id
    })
  })
}

function buildBessFacility() {
  // 4 Containerized Megapack Enclosures (BESS-01)
  const bessX = -105
  const bessZ = 0

  for (let i = 0; i < 4; i++) {
    const containerGeo = new THREE.BoxGeometry(4.5, 3.2, 10)
    const containerMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.6,
      roughness: 0.3
    })
    const container = new THREE.Mesh(containerGeo, containerMat)
    container.position.set(bessX, 1.6, bessZ + (i * 12) - 18)
    container.castShadow = true
    container.receiveShadow = true
    container.userData = {
      type: 'BESS_CONTAINER',
      id: `BESS-01:RACK-${i + 1}`
    }
    scene.add(container)
    bessContainers.push(container)
    clickableObjects.push(container)

    // Glowing LED energy flow strip on container side
    const ledStripGeo = new THREE.BoxGeometry(0.1, 0.4, 8)
    const ledStripMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4 })
    const ledStrip = new THREE.Mesh(ledStripGeo, ledStripMat)
    ledStrip.position.set(bessX + 2.3, 2.0, bessZ + (i * 12) - 18)
    scene.add(ledStrip)
  }
}

function buildSubstation() {
  // High Voltage Step-Up Substation
  const subX = 105
  const subZ = 0

  // Transformer Unit
  const xfGeo = new THREE.BoxGeometry(8, 6, 8)
  const xfMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6 })
  const transformer = new THREE.Mesh(xfGeo, xfMat)
  transformer.position.set(subX, 3, subZ)
  transformer.castShadow = true
  transformer.receiveShadow = true
  transformer.userData = {
    type: 'SUBSTATION',
    id: 'SUB-230KV-01'
  }
  scene.add(transformer)
  clickableObjects.push(transformer)

  // Transmission Pylon (Lattice tower)
  const pylonGeo = new THREE.CylinderGeometry(0.8, 3.5, 25, 4)
  const pylonMat = new THREE.MeshStandardMaterial({ color: 0x64748b, wireframe: true })
  const pylon = new THREE.Mesh(pylonGeo, pylonMat)
  pylon.position.set(subX + 15, 12.5, subZ)
  scene.add(pylon)
}

function updateSunPosition() {
  if (!dirSunLight) return
  // Convert spherical coordinates (azimuth, elevation) to Cartesian (x, y, z)
  const elevRad = THREE.MathUtils.degToRad(Math.max(2.0, sunElevation.value))
  const azimRad = THREE.MathUtils.degToRad(sunAzimuth.value)

  const radius = 180
  const y = radius * Math.sin(elevRad)
  const horizDist = radius * Math.cos(elevRad)
  const x = horizDist * Math.sin(azimRad)
  const z = -horizDist * Math.cos(azimRad)

  dirSunLight.position.set(x, y, z)
  dirSunLight.target.position.set(0, 0, 0)
  dirSunLight.target.updateMatrixWorld()

  // Adjust ambient and directional light intensity based on elevation
  const dayFactor = Math.max(0.15, Math.sin(elevRad))
  dirSunLight.intensity = dayFactor * 2.2
  ambientLight.intensity = 0.3 + dayFactor * 0.4
}

function updateTrackerTilt(tiltDeg) {
  // Tilt is around the Z-axis (North-South horizontal torque tube)
  // Positive tilt = West (afternoon), Negative tilt = East (morning)
  const tiltRad = THREE.MathUtils.degToRad(tiltDeg)
  trackerRowGroups.forEach((row) => {
    row.group.rotation.z = -tiltRad
  })
}

function updateVisualMode(mode) {
  const isThermal = mode === 'THERMAL'
  const isFaults = mode === 'FAULTS'

  // Look for active string faults in telemetry
  const faults = props.telemetry?.disturbances?.string_faults || {}

  trackerRowGroups.forEach((row) => {
    const faultKey = `${row.inverterId}:${row.stringId}`
    const hasFault = Boolean(faults[faultKey])

    if (isFaults && hasFault) {
      row.mesh.material = faultMaterial
    } else if (isThermal) {
      // Thermal false-color based on temperature
      // Inverter temp ~55C to 95C
      const invData = props.telemetry?.inverters?.find(inv => inv.inverter_id === row.inverterId)
      const tempC = invData?.inverter_temp_c || 55.0
      const normTemp = Math.min(1.0, Math.max(0.0, (tempC - 40.0) / 50.0)) // 0 (40C) to 1 (90C)
      
      const thermalColor = new THREE.Color().setHSL(0.6 * (1.0 - normTemp), 1.0, 0.5)
      const customThermalMat = new THREE.MeshStandardMaterial({
        color: thermalColor,
        roughness: 0.4
      })
      row.mesh.material = customThermalMat
    } else {
      row.mesh.material = pbrPanelMaterial
    }
  })
}

function animate() {
  animationFrameId = requestAnimationFrame(animate)

  // Rotate wind turbine blades based on telemetry RPM
  const rpm = props.telemetry?.turbines?.[0]?.rotor_rpm || 12.0
  const angularVelocity = (rpm * 2 * Math.PI) / 60 / 60 // rad per frame at 60fps

  turbineRotors.forEach((turb) => {
    turb.rotor.rotation.z += angularVelocity
  })

  // Pulsing fault glow if active
  if (visualMode.value === 'FAULTS' && faultMaterial) {
    const pulse = 0.5 + 0.5 * Math.sin(Date.now() * 0.008)
    faultMaterial.emissiveIntensity = 0.4 + pulse * 0.8
  }

  controls.update()
  renderer.render(scene, camera)
}

function setCameraPreset(preset) {
  activePreset.value = preset
  if (!camera || !controls) return

  const presets = {
    overview: { pos: [0, 75, 130], target: [0, 5, 0] },
    solar: { pos: [-10, 30, 35], target: [-10, 5, 0] },
    wind: { pos: [0, 45, -40], target: [0, 35, -100] },
    bess: { pos: [-80, 20, 25], target: [-105, 5, 0] },
    substation: { pos: [85, 25, 25], target: [105, 5, 0] }
  }

  const p = presets[preset] || presets.overview
  camera.position.set(...p.pos)
  controls.target.set(...p.target)
}

function onCanvasClick(event) {
  const rect = renderer.domElement.getBoundingClientRect()
  mousePointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mousePointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mousePointer, camera)
  const intersects = raycaster.intersectObjects(clickableObjects, true)

  if (intersects.length > 0) {
    const obj = intersects[0].object
    const data = obj.userData || {}

    if (data.type === 'STRING_TABLE') {
      const invData = props.telemetry?.inverters?.find(inv => inv.inverter_id === data.inverterId)
      const strData = invData?.strings?.[data.stringIndex] || {}
      const fault = props.telemetry?.disturbances?.string_faults?.[data.id]

      inspectedAsset.value = {
        type: 'PV String Table',
        id: data.id,
        metrics: {
          'Voltage': `${strData.voltage_v || 850.0} V`,
          'Current': `${strData.current_a || 18.5} A`,
          'DC Power': `${strData.power_kw || 314.5} kW`,
          'Tracker Tilt': `${currentTilt.value.toFixed(1)}°`,
          'Inverter Temp': `${invData?.inverter_temp_c || 55.0} °C`
        },
        fault: fault ? `ALARM: ${fault}` : null
      }
    } else if (data.type === 'INVERTER') {
      const invData = props.telemetry?.inverters?.find(inv => inv.inverter_id === data.id)
      inspectedAsset.value = {
        type: 'Central Inverter Skid',
        id: data.id,
        metrics: {
          'AC Power': `${invData?.ac_power_kw || 4850.0} kW`,
          'DC Power': `${invData?.dc_power_kw || 4920.0} kW`,
          'Heatsink Temp': `${invData?.inverter_temp_c || 58.2} °C`,
          'Status': invData?.status || 'NORMAL',
          'Strings Online': `${invData?.strings?.length || 8} / 8`
        },
        fault: invData?.inverter_temp_c > 90 ? 'OVERHEAT WARNING (>90°C)' : null
      }
    } else if (data.type === 'TURBINE') {
      const turbData = props.telemetry?.turbines?.find(t => t.turbine_id === data.id) || props.telemetry?.turbines?.[0]
      inspectedAsset.value = {
        type: 'Wind Turbine (2.5 MW)',
        id: data.id,
        metrics: {
          'Active Power': `${turbData?.power_kw || 2450.0} kW`,
          'Rotor Speed': `${turbData?.rotor_rpm || 16.2} RPM`,
          'Wind Speed': `${turbData?.wind_speed_ms || 8.5} m/s`,
          'Yaw Heading': `${(props.telemetry?.spatial_tracking?.wind_yaw_deg || 245.0).toFixed(1)}°`,
          'Status': 'SYNCHRONIZED'
        }
      }
    } else if (data.type === 'BESS_CONTAINER') {
      inspectedAsset.value = {
        type: 'BESS Megapack Rack',
        id: data.id,
        metrics: {
          'Capacity': '10.0 MWh (LiFePO4)',
          'State of Charge': `${props.telemetry?.battery_soc_pct || 65.0}%`,
          'Power Flow': `${props.telemetry?.bess_dispatch_kw || 0.0} kW`,
          'Thermal Loop': '24.2 °C (Liquid Cooled)',
          'Health (SOH)': '99.4%'
        }
      }
    } else if (data.type === 'SUBSTATION') {
      inspectedAsset.value = {
        type: 'Main Substation',
        id: 'SUB-230KV-01',
        metrics: {
          'Net Injected': `${Math.round(props.telemetry?.injected_kw || props.telemetry?.total_renewable_kw || 20000)} kW`,
          'Bus Voltage': '230.0 kV',
          'Grid Frequency': '60.00 Hz',
          'Tariff': `$${props.telemetry?.tariff_usd_kwh || 0.14}/kWh`,
          'Contract Schedule': `${props.telemetry?.committed_schedule_kw || 20300} kW`
        }
      }
    }
  }
}

function onWindowResize() {
  if (!canvasContainer.value || !renderer || !camera) return
  const width = canvasContainer.value.clientWidth
  const height = canvasContainer.value.clientHeight
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

function close() {
  emit('close')
}

// Watchers
watch(() => currentTilt.value, (newTilt) => {
  updateTrackerTilt(newTilt)
})

watch(() => [sunElevation.value, sunAzimuth.value], () => {
  updateSunPosition()
})

watch(() => visualMode.value, (newMode) => {
  updateVisualMode(newMode)
})

watch(() => props.telemetry, () => {
  if (visualMode.value !== 'PBR') {
    updateVisualMode(visualMode.value)
  }
}, { deep: true })

onMounted(() => {
  initThree()
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  window.removeEventListener('resize', onWindowResize)
  if (renderer?.domElement) {
    renderer.domElement.removeEventListener('click', onCanvasClick)
    renderer.dispose()
  }
  controls?.dispose()
})
</script>

<style scoped>
.twin-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(4, 8, 16, 0.88);
  backdrop-filter: blur(10px);
  z-index: 1050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
}

.twin-modal-container {
  width: 96vw;
  height: 94vh;
  background: #080e1a;
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 40px rgba(6, 182, 212, 0.15);
  overflow: hidden;
}

/* Header */
.twin-header {
  height: 64px;
  background: #0b1324;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.25rem;
  flex-shrink: 0;
}

.twin-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.twin-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.twin-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.04em;
}

.twin-sub {
  color: #06b6d4;
  font-weight: 600;
}

.twin-loc {
  font-size: 0.72rem;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

/* Telemetry Badges Strip */
.twin-telemetry-strip {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.twin-badge {
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
}

.tb-label {
  font-size: 0.62rem;
  color: #94a3b8;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.tb-val {
  font-size: 0.85rem;
  font-weight: 700;
}

.tb-status-pill {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  text-transform: uppercase;
  margin-top: 0.1rem;
}

.pill-emerald { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.pill-amber { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.pill-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.pill-slate { background: rgba(100, 116, 139, 0.15); color: #94a3b8; }

/* Visual Mode & Controls */
.twin-controls-wrap {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.mode-selector {
  display: flex;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 2px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.mode-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn:hover {
  color: #f1f5f9;
}

.mode-btn.active {
  background: #0ea5e9;
  color: #fff;
  box-shadow: 0 0 10px rgba(14, 165, 233, 0.4);
}

.mode-btn-thermal.active {
  background: #10b981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}

.mode-btn-fault.active {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
}

.twin-close-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.twin-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.4);
}

/* Canvas Viewport */
.twin-canvas-wrapper {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* Floating Camera Toolbar */
.camera-toolbar {
  position: absolute;
  top: 16px;
  left: 16px;
  background: rgba(11, 19, 36, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 0.35rem 0.6rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  z-index: 10;
}

.cam-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: #64748b;
  margin-right: 0.2rem;
}

.camera-toolbar button {
  background: transparent;
  border: 1px solid transparent;
  color: #94a3b8;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.camera-toolbar button:hover {
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.05);
}

.camera-toolbar button.active {
  background: rgba(6, 182, 212, 0.2);
  color: #06b6d4;
  border-color: rgba(6, 182, 212, 0.4);
}

/* Manual Tracker Override Card */
.tracker-override-card {
  position: absolute;
  bottom: 16px;
  left: 16px;
  width: 290px;
  background: rgba(11, 19, 36, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 8px;
  padding: 0.75rem;
  z-index: 10;
}

.override-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.68rem;
  font-weight: 700;
  color: #94a3b8;
  margin-bottom: 0.5rem;
}

.override-toggle {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}

.override-toggle.active {
  background: rgba(168, 85, 247, 0.25);
  color: #c084fc;
  border-color: rgba(168, 85, 247, 0.5);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.scada-range {
  width: 100%;
  accent-color: #06b6d4;
  cursor: pointer;
}

.override-info {
  font-size: 0.75rem;
  color: #94a3b8;
}

/* Raycasting SCADA Asset HUD */
.asset-hud-card {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 280px;
  background: rgba(11, 19, 36, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(6, 182, 212, 0.4);
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6);
  z-index: 10;
  overflow: hidden;
}

.asset-hud-header {
  background: rgba(6, 182, 212, 0.12);
  border-bottom: 1px solid rgba(6, 182, 212, 0.2);
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.asset-type-tag {
  font-size: 0.62rem;
  font-weight: 700;
  background: #06b6d4;
  color: #040810;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  text-transform: uppercase;
}

.asset-id {
  font-size: 0.8rem;
  font-weight: 700;
  color: #f1f5f9;
  font-family: 'JetBrains Mono', monospace;
}

.hud-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 1.1rem;
  cursor: pointer;
}

.asset-hud-body {
  padding: 0.75rem;
}

.hud-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 0.75rem;
}

.hud-label {
  color: #94a3b8;
}

.hud-val {
  color: #f1f5f9;
  font-weight: 600;
}

.hud-alert-banner {
  margin-top: 0.5rem;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 700;
}

/* Legend */
.twin-legend {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: rgba(11, 19, 36, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 0.4rem 0.75rem;
  font-size: 0.7rem;
  color: #94a3b8;
  z-index: 10;
}

.thermal-legend {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.thermal-bar {
  width: 100px;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, #3b82f6, #10b981, #f59e0b, #ef4444);
}

.fault-legend {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dot-normal {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.dot-fault {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.pbr-legend {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
}
</style>
