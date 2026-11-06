<script setup>
// Single-series line chart. Measures its own width so text stays at true size
// instead of scaling with a viewBox. `points` is [{ x, y, tip }], x numeric.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  points: { type: Array, required: true },
  title: { type: String, required: true },
  height: { type: Number, default: 170 },
  yTicks: { type: Array, default: null }, // [{ value, label }] for a fixed scale
  xLabels: { type: Array, default: () => [] }, // [start, end]
  color: { type: String, default: 'var(--red)' },
})

const box = ref(null)
const width = ref(320)
const hover = ref(null)
const PAD = { left: 62, right: 10, top: 12, bottom: 22 }
let observer

onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    width.value = entry.contentRect.width
  })
  observer.observe(box.value)
})
onBeforeUnmount(() => observer?.disconnect())

const yDomain = computed(() => {
  if (props.yTicks) {
    const values = props.yTicks.map((t) => t.value)
    return [Math.min(...values), Math.max(...values)]
  }
  const ys = props.points.map((p) => p.y)
  const lo = Math.min(...ys)
  const hi = Math.max(...ys)
  const pad = Math.max((hi - lo) * 0.2, 0.5)
  return [lo - pad, hi + pad]
})

const ticks = computed(() => {
  if (props.yTicks) return props.yTicks
  const [lo, hi] = yDomain.value
  return [lo, (lo + hi) / 2, hi].map((value) => ({ value, label: value.toFixed(1) }))
})

const xDomain = computed(() => {
  const xs = props.points.map((p) => p.x)
  return [Math.min(...xs), Math.max(...xs)]
})

const sx = (x) => {
  const [lo, hi] = xDomain.value
  const inner = width.value - PAD.left - PAD.right
  return PAD.left + (hi === lo ? inner / 2 : ((x - lo) / (hi - lo)) * inner)
}
const sy = (y) => {
  const [lo, hi] = yDomain.value
  return PAD.top + (1 - (y - lo) / (hi - lo)) * (props.height - PAD.top - PAD.bottom)
}

const line = computed(() =>
  props.points.map((p, i) => `${i ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' '),
)

function track(event) {
  const left = box.value.getBoundingClientRect().left
  const x = event.clientX - left
  let best = 0
  props.points.forEach((p, i) => {
    if (Math.abs(sx(p.x) - x) < Math.abs(sx(props.points[best].x) - x)) best = i
  })
  hover.value = best
}

const active = computed(() => (hover.value == null ? null : props.points[hover.value]))
const last = computed(() => props.points[props.points.length - 1])
const tipLeft = computed(() => {
  const x = sx(active.value.x)
  return `${Math.min(width.value - 70, Math.max(70, x))}px`
})
</script>

<template>
  <div ref="box" class="chart" @pointermove="track" @pointerleave="hover = null">
    <svg :height="height" role="img" :aria-label="title">
      <g v-for="t in ticks" :key="t.value">
        <line :x1="PAD.left" :x2="width - PAD.right" :y1="sy(t.value)" :y2="sy(t.value)"
          stroke="var(--ink-3)" stroke-width="1" />
        <text :x="PAD.left - 8" :y="sy(t.value) + 4" text-anchor="end">{{ t.label }}</text>
      </g>
      <text v-if="xLabels[0]" :x="PAD.left" :y="height - 4">{{ xLabels[0] }}</text>
      <text v-if="xLabels[1]" :x="width - PAD.right" :y="height - 4" text-anchor="end">{{ xLabels[1] }}</text>

      <path :d="line" fill="none" :stroke="color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
      <circle v-for="(p, i) in points" :key="i" :cx="sx(p.x)" :cy="sy(p.y)" r="3" :fill="color" />
      <circle v-if="!active && last" :cx="sx(last.x)" :cy="sy(last.y)" r="5" :fill="color"
        stroke="var(--ink-2)" stroke-width="2" />

      <template v-if="active">
        <line :x1="sx(active.x)" :x2="sx(active.x)" :y1="PAD.top" :y2="height - PAD.bottom"
          stroke="var(--dust)" stroke-width="1" />
        <circle :cx="sx(active.x)" :cy="sy(active.y)" r="5" :fill="color" stroke="var(--ink-2)" stroke-width="2" />
      </template>
    </svg>
    <span v-if="active" class="tip" :style="{ left: tipLeft }">{{ active.tip }}</span>
  </div>
</template>
