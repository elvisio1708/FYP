<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import Icon from '../components/Icon.vue'
import RatingForm from '../components/RatingForm.vue'
import * as bell from '../lib/bell'
import { clock } from '../lib/format'
import { confirmDialog, toast } from '../lib/store'
import { buildSteps, stepLabel, stepSeconds, totalSeconds } from '../lib/workout'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()

const MUTE_KEY = 'seconds-out-muted'
const readMuted = () => {
  try {
    return localStorage.getItem(MUTE_KEY) === '1'
  } catch {
    return false
  }
}

const stage = ref('loading') // loading | ready | ring | done | missing
const session = ref(null)
const steps = ref([])
const index = ref(0)
const remaining = ref(0) // ms left in a timed step
const paused = ref(false)
const muted = ref(readMuted())
const busy = ref(false)
const elapsedTotal = ref(0)

let endAt = 0
let interval = null
let startedAt = 0
let lastSecond = null
let wakeLock = null
bell.setMuted(muted.value)

onMounted(async () => {
  try {
    const { plan } = await api.currentPlan()
    session.value = plan?.sessions.find((s) => s.id === Number(props.id)) ?? null
    if (!session.value) {
      stage.value = 'missing'
    } else if (session.value.completed) {
      router.replace(`/session/${props.id}`)
    } else {
      steps.value = buildSteps(session.value.exercises)
      stage.value = 'ready'
    }
  } catch (e) {
    toast(e.message, 'bad')
    stage.value = 'missing'
  }
  window.addEventListener('keydown', onKey)
  window.addEventListener('keyup', onKeyUp)
  document.addEventListener('visibilitychange', keepAwake)
})

onBeforeUnmount(() => {
  clearInterval(interval)
  wakeLock?.release?.().catch(() => {})
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('keyup', onKeyUp)
  document.removeEventListener('visibilitychange', keepAwake)
})

const step = computed(() => steps.value[index.value])
const seconds = computed(() => Math.ceil(remaining.value / 1000))
const isTimed = computed(() => !!step.value?.seconds)
const isFinalTen = computed(() => isTimed.value && step.value.phase === 'work' && step.value.seconds >= 30 && seconds.value <= 10)

const ringClass = computed(() => {
  if (paused.value) return 'paused'
  if (isFinalTen.value) return 'final'
  return step.value?.phase
})

const totalPlanned = computed(() => totalSeconds(steps.value))
const progress = computed(() => {
  const before = steps.value.slice(0, index.value).reduce((sum, s) => sum + stepSeconds(s), 0)
  const within = isTimed.value ? step.value.seconds - remaining.value / 1000 : 0
  return Math.min(100, ((before + within) / (totalPlanned.value || 1)) * 100)
})

const roundsDone = computed(() => {
  const worked = steps.value.slice(0, index.value + 1)
  return worked.filter((s) => s.round || s.station === 1).length
})

async function keepAwake() {
  if (stage.value !== 'ring' || document.visibilityState !== 'visible') return
  try {
    wakeLock = await navigator.wakeLock?.request('screen')
  } catch {
    /* unsupported or refused: the timer still works, the screen may just dim */
  }
}

function begin() {
  bell.unlock()
  stage.value = 'ring'
  startedAt = Date.now()
  keepAwake()
  enter(0)
  interval = setInterval(tick, 100)
}

function enter(i) {
  if (i >= steps.value.length) {
    finish()
    return
  }
  index.value = i
  paused.value = false
  lastSecond = null
  const current = steps.value[i]
  if (current.phase === 'rest') bell.roundEnd()
  else bell.roundStart()
  if (current.seconds) {
    remaining.value = current.seconds * 1000
    endAt = Date.now() + remaining.value
  }
}

// Reads the wall clock rather than counting ticks, so a throttled background
// tab can't make the round run long.
function tick() {
  if (paused.value || stage.value !== 'ring' || !isTimed.value) return
  remaining.value = endAt - Date.now()
  const whole = seconds.value
  if (whole !== lastSecond) {
    lastSecond = whole
    if (isFinalTen.value && whole === 10) bell.tenSeconds()
    if (step.value.phase === 'rest' && whole <= 3 && whole > 0) bell.tick()
  }
  if (remaining.value <= 0) enter(index.value + 1)
}

function togglePause() {
  if (!isTimed.value) return
  if (paused.value) endAt = Date.now() + remaining.value
  paused.value = !paused.value
}

const skip = () => enter(index.value + 1)

function back() {
  let i = index.value - 1
  while (i > 0 && steps.value[i].phase === 'rest') i--
  enter(Math.max(0, i))
}

function toggleMute() {
  muted.value = !muted.value
  bell.setMuted(muted.value)
  try {
    localStorage.setItem(MUTE_KEY, muted.value ? '1' : '0')
  } catch {
    /* preference just won't persist */
  }
}

async function endEarly() {
  const wasPaused = paused.value
  if (!wasPaused && isTimed.value) togglePause()
  const ok = await confirmDialog({
    title: 'End this session?',
    body: 'You can still log what you did.',
    confirmLabel: 'End session',
    cancelLabel: 'Keep going',
  })
  if (ok) finish()
  else if (!wasPaused && isTimed.value) togglePause()
}

function finish() {
  clearInterval(interval)
  elapsedTotal.value = Math.round((Date.now() - startedAt) / 1000)
  stage.value = 'done'
  bell.roundEnd()
  wakeLock?.release?.().catch(() => {})
}

async function log(values) {
  busy.value = true
  try {
    const res = await api.completeSession(session.value.id, values)
    const next = res.next_plan_intensity
    toast(next > 1 ? 'Logged. Your next plan will push harder.' : next < 1 ? 'Logged. Your next plan will ease off.' : 'Logged. Good work.')
    router.replace('/')
  } catch (e) {
    toast(e.message, 'bad')
    busy.value = false
  }
}

function onKey(event) {
  if (stage.value !== 'ring' || document.querySelector('dialog[open]')) return
  if (event.code === 'Space') {
    event.preventDefault()
    event.target.blur?.() // a focused button would also fire on key-up
    if (isTimed.value) togglePause()
    else skip()
  } else if (event.code === 'ArrowRight') skip()
  else if (event.code === 'ArrowLeft') back()
}

// On key-up: opened on key-down, the same press would also close the new dialog.
function onKeyUp(event) {
  if (event.code !== 'Escape' || stage.value !== 'ring' || document.querySelector('dialog[open]')) return
  endEarly()
}
</script>

<template>
  <div v-if="stage === 'loading'" class="ring"><div class="center-load" style="flex: 1">Loading…</div></div>

  <div v-else-if="stage === 'missing'" class="ring">
    <div class="ring-start">
      <h1 class="display">Session not found</h1>
      <button class="btn bone big" @click="router.replace('/')">Back to today</button>
    </div>
  </div>

  <div v-else-if="stage === 'ready'" class="ring">
    <div class="ring-top">
      <button class="icon-btn" aria-label="Back" @click="router.back()"><Icon name="back" /></button>
    </div>
    <div class="ring-start">
      <p class="eyebrow">Week {{ session.week }} · about {{ session.duration_minutes }} minutes</p>
      <h1 class="display">{{ session.title }}</h1>
      <p class="muted">
        Turn your volume up: a bell starts each round and three bells end it. On a computer, Space pauses
        and the arrow keys skip.
      </p>
      <button class="btn primary big block" @click="begin"><Icon name="play" /> Seconds out</button>
    </div>
  </div>

  <div v-else-if="stage === 'ring'" class="ring" :class="ringClass">
    <div class="ring-top">
      <button class="icon-btn" aria-label="End session" @click="endEarly"><Icon name="close" /></button>
      <span class="ring-label" style="font-size: 1rem">{{ session.title }}</span>
      <button class="icon-btn" :aria-label="muted ? 'Turn sound on' : 'Turn sound off'" :aria-pressed="muted"
        @click="toggleMute"><Icon :name="muted ? 'mute' : 'sound'" /></button>
    </div>
    <div class="ring-track"><i :style="{ width: `${progress}%` }"></i></div>

    <div class="ring-mid">
      <p class="ring-label">{{ paused ? 'Paused' : stepLabel(step) }}</p>
      <template v-if="isTimed">
        <p v-if="step.phase !== 'rest'" class="ring-title">{{ step.title }}</p>
        <div class="ring-time" role="timer" aria-live="off">{{ clock(remaining / 1000) }}</div>
      </template>
      <template v-else>
        <p class="ring-title">{{ step.title }}</p>
        <div class="ring-reps">{{ step.reps ? `${step.reps} reps` : 'Go' }}</div>
      </template>
      <p v-if="step.notes" class="ring-desc">{{ step.notes }}</p>
      <p v-else-if="step.description" class="ring-desc">{{ step.description }}</p>
    </div>

    <p class="ring-next"><template v-if="step.next">Next: {{ step.next }}</template></p>
    <div class="ring-controls">
      <button class="icon-btn" aria-label="Previous" :disabled="index === 0" @click="back"><Icon name="prev" /></button>
      <button v-if="isTimed" class="icon-btn main" :aria-label="paused ? 'Resume' : 'Pause'" @click="togglePause">
        <Icon :name="paused ? 'play' : 'pause'" :size="32" />
      </button>
      <button v-else class="icon-btn main" aria-label="Set done" @click="skip"><Icon name="check" :size="32" /></button>
      <button class="icon-btn" aria-label="Skip" @click="skip"><Icon name="next" /></button>
    </div>
  </div>

  <div v-else class="ring">
    <div class="ring-start">
      <p class="eyebrow">{{ clock(elapsedTotal) }} on the clock<template v-if="roundsDone"> · {{ roundsDone }} rounds</template></p>
      <h1 class="display">Session done</h1>
      <RatingForm :busy="busy" @submit="log" />
      <button class="link" style="justify-self: start; align-self: flex-start" @click="router.replace('/')">
        Leave without logging
      </button>
    </div>
  </div>
</template>
