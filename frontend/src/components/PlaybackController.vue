<template>
  <div class="glass-panel playback-card" :class="{ 'mode-playback': isPlaybackMode }">
    <div class="playback-header">
      <!-- Mode Toggle -->
      <div class="mode-toggle-group">
        <button 
          @click="setMode('live')" 
          class="mode-btn" 
          :class="{ active: !isPlaybackMode }"
        >
          <span class="status-dot" :class="{ active: !isPlaybackMode }"></span>
          LIVE 2s TELEMETRY
        </button>
        <button 
          @click="setMode('playback')" 
          class="mode-btn" 
          :class="{ active: isPlaybackMode }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          HISTORICAL TIME-MACHINE
        </button>
      </div>

      <!-- Incident Selector (Playback Mode Only) -->
      <div v-if="isPlaybackMode" class="incident-selector-wrap">
        <label class="incident-label">INCIDENT ARCHIVE:</label>
        <select v-model="selectedScenarioId" @change="loadScenario" class="incident-select">
          <option v-for="s in scenarios" :key="s.id" :value="s.id">
            [{{ s.id }}] {{ s.title }} ({{ s.duration_sec }}s)
          </option>
        </select>
      </div>

      <!-- Right Meta Status -->
      <div class="playback-meta">
        <span v-if="isPlaybackMode" class="badge badge-amber">
          PLAYBACK FRAME: {{ currentFrameIndex + 1 }} / {{ totalFrames }}
        </span>
        <span v-else class="badge badge-emerald">
          <span class="status-dot active"></span>
          SUB-SECOND SYNCED
        </span>
      </div>
    </div>

    <!-- Playback Scrubber Bar (Visible only in Playback Mode) -->
    <div v-if="isPlaybackMode" class="playback-controls-body">
      <!-- Timeline Scrubber with Markers -->
      <div class="timeline-container">
        <input 
          type="range" 
          min="0" 
          :max="Math.max(0, totalFrames - 1)" 
          v-model.number="currentFrameIndex"
          @input="handleSeek"
          class="scrubber-slider"
        />
        <div class="timeline-ticks">
          <span class="mono-val">00:00</span>
          <span class="mono-val text-amber" v-if="activeScenario">
            Incident Peak ({{ activeScenario.peak_sec }}s)
          </span>
          <span class="mono-val">{{ formatDuration(activeScenario?.duration_sec || 120) }}</span>
        </div>
      </div>

      <!-- Action Button Controls -->
      <div class="controls-toolbar">
        <div class="btn-group-left">
          <!-- Play / Pause -->
          <button @click="togglePlay" class="btn-scada btn-scada-cyan btn-play">
            <template v-if="!isPlaying">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              PLAY
            </template>
            <template v-else>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect width="4" height="16" x="6" y="4"/><rect width="4" height="16" x="14" y="4"/></svg>
              PAUSE
            </template>
          </button>

          <!-- Step Backward -->
          <button @click="step(-1)" class="btn-scada" title="Step Back 2s">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="19 20 9 12 19 4 19 20"/><line x1="5" x2="5" y1="19" y2="5"/></svg>
            -2s
          </button>

          <!-- Step Forward -->
          <button @click="step(1)" class="btn-scada" title="Step Forward 2s">
            +2s
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" x2="19" y1="5" y2="19"/></svg>
          </button>

          <!-- Jump to Peak -->
          <button @click="jumpToPeak" class="btn-scada btn-scada-amber">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            JUMP TO PEAK
          </button>
        </div>

        <!-- Speed Selector -->
        <div class="speed-group">
          <span class="speed-label">SPEED:</span>
          <button 
            v-for="spd in [1, 2, 4]" 
            :key="spd" 
            @click="setSpeed(spd)" 
            class="speed-btn" 
            :class="{ active: playbackSpeed === spd }"
          >
            {{ spd }}x
          </button>
        </div>

        <!-- Time & Status Readout -->
        <div class="time-readout mono-val">
          <span class="time-main">{{ currentTimestamp }}</span>
          <span class="time-sub">Offset: +{{ currentSecondOffset }}s</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['mode-change', 'frame-update'])

const isPlaybackMode = ref(false)
const scenarios = ref([])
const selectedScenarioId = ref('INC-2026-041')
const frames = ref([])
const currentFrameIndex = ref(0)
const isPlaying = ref(false)
const playbackSpeed = ref(1)
let playTimer = null

const totalFrames = computed(() => frames.value.length)
const activeScenario = computed(() => scenarios.value.find(s => s.id === selectedScenarioId.value))

const currentFrame = computed(() => frames.value[currentFrameIndex.value] || null)
const currentSecondOffset = computed(() => currentFrame.value?.second_offset || 0)
const currentTimestamp = computed(() => {
  if (!currentFrame.value?.timestamp) return '--:--:--'
  try {
    return new Date(currentFrame.value.timestamp).toTimeString().split(' ')[0]
  } catch {
    return currentFrame.value.timestamp
  }
})

onMounted(async () => {
  await fetchCatalog()
})

onUnmounted(() => {
  stopPlayTimer()
})

async function fetchCatalog() {
  try {
    const res = await fetch('/api/scenarios/catalog')
    const data = await res.json()
    scenarios.value = data
    if (data.length) {
      selectedScenarioId.value = data[0].id
    }
  } catch (err) {
    console.error('Error fetching scenario catalog:', err)
  }
}

async function loadScenario() {
  stopPlayTimer()
  isPlaying.value = false
  currentFrameIndex.value = 0
  try {
    const res = await fetch(`/api/scenarios/${selectedScenarioId.value}/frames`)
    const data = await res.json()
    frames.value = data.frames || []
    if (frames.value.length) {
      broadcastFrame()
    }
  } catch (err) {
    console.error('Error loading scenario frames:', err)
  }
}

function setMode(mode) {
  if (mode === 'live') {
    isPlaybackMode.value = false
    stopPlayTimer()
    isPlaying.value = false
    emit('mode-change', 'live')
  } else {
    isPlaybackMode.value = true
    if (!frames.value.length) {
      loadScenario()
    } else {
      broadcastFrame()
    }
    emit('mode-change', 'playback')
  }
}

function togglePlay() {
  if (isPlaying.value) {
    stopPlayTimer()
    isPlaying.value = false
  } else {
    isPlaying.value = true
    startPlayTimer()
  }
}

function startPlayTimer() {
  stopPlayTimer()
  // Normal 2s interval scaled by playback speed (e.g. 2x = 1000ms, 4x = 500ms)
  const intervalMs = Math.max(200, 2000 / playbackSpeed.value)
  playTimer = setInterval(() => {
    if (currentFrameIndex.value < totalFrames.value - 1) {
      currentFrameIndex.value++
      broadcastFrame()
    } else {
      // Loop or pause at end
      currentFrameIndex.value = 0
      broadcastFrame()
    }
  }, intervalMs)
}

function stopPlayTimer() {
  if (playTimer) {
    clearInterval(playTimer)
    playTimer = null
  }
}

function setSpeed(spd) {
  playbackSpeed.value = spd
  if (isPlaying.value) {
    startPlayTimer()
  }
}

function step(delta) {
  stopPlayTimer()
  isPlaying.value = false
  const target = currentFrameIndex.value + delta
  if (target >= 0 && target < totalFrames.value) {
    currentFrameIndex.value = target
    broadcastFrame()
  }
}

function handleSeek() {
  broadcastFrame()
}

function jumpToPeak() {
  if (!activeScenario.value) return
  const peakSec = activeScenario.value.peak_sec || 0
  const peakIdx = Math.min(totalFrames.value - 1, Math.round(peakSec / 2))
  currentFrameIndex.value = peakIdx
  broadcastFrame()
}

function broadcastFrame() {
  if (currentFrame.value) {
    emit('frame-update', currentFrame.value)
  }
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.playback-card {
  display: flex;
  flex-direction: column;
  padding: 14px 20px;
  background: rgba(13, 17, 26, 0.95);
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
}

.playback-card.mode-playback {
  border-color: rgba(245, 158, 11, 0.4);
  box-shadow: 0 0 24px rgba(245, 158, 11, 0.12);
}

.playback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.mode-toggle-group {
  display: flex;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 3px;
  gap: 4px;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  background: none;
  border: none;
  color: var(--text-muted);
  transition: all 0.2s ease;
}

.mode-btn.active {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.mode-btn:hover:not(.active) {
  color: var(--text-secondary);
}

.incident-selector-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  max-width: 600px;
}

.incident-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--accent-amber);
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.incident-select {
  flex: 1;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-family: var(--font-sans);
  cursor: pointer;
}
.incident-select:focus {
  outline: none;
  border-color: var(--accent-amber);
}

.playback-meta {
  display: flex;
  align-items: center;
}

.playback-controls-body {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.scrubber-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  transition: background 0.2s;
}

.scrubber-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent-amber);
  cursor: pointer;
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.6);
  transition: transform 0.1s ease;
}

.scrubber-slider::-webkit-slider-thumb:hover {
  transform: scale(1.25);
}

.timeline-ticks {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
  color: var(--text-muted);
}

.controls-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.btn-group-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-play {
  padding: 6px 16px;
  font-weight: 700;
}

.speed-group {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 0, 0, 0.3);
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.speed-label {
  font-size: 0.68rem;
  color: var(--text-muted);
  font-weight: 700;
}

.speed-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}

.speed-btn.active {
  background: rgba(255, 255, 255, 0.1);
  color: var(--accent-cyan);
}

.time-readout {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.time-main {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
}

.time-sub {
  font-size: 0.68rem;
  color: var(--text-muted);
}
</style>
