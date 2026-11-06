<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import BarChart from '../components/BarChart.vue'
import Icon from '../components/Icon.vue'
import LineChart from '../components/LineChart.vue'
import Ropes from '../components/Ropes.vue'
import { RATINGS, fmtDate, isoToday, parseDay } from '../lib/format'
import { toast } from '../lib/store'

const METRICS = {
  weight_kg: { label: 'Weight', unit: 'kg' },
  waist_cm: { label: 'Waist', unit: 'cm' },
  body_fat_pct: { label: 'Body fat', unit: '%' },
}

const stats = ref(null)
const entries = ref([])
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const fields = ref({})
const form = reactive({ metric: 'weight_kg', value: null, date: isoToday() })
const today = isoToday()

onMounted(async () => {
  try {
    const [s, p] = await Promise.all([api.stats(), api.progress()])
    stats.value = s
    entries.value = p.progress
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

const short = (iso) => fmtDate(iso, { day: 'numeric', month: 'short' })

const weekBars = computed(() =>
  stats.value.by_week.map((w) => ({
    key: w.week_start,
    label: short(w.week_start),
    value: w.sessions,
    tip: `${w.sessions} session${w.sessions === 1 ? '' : 's'}, ${w.minutes} min`,
  })),
)

const RATING_TICKS = [
  { value: 1, label: 'Too easy' },
  { value: 3, label: 'About right' },
  { value: 5, label: 'Too hard' },
]

const ratingPoints = computed(() =>
  stats.value.ratings.map((r, i) => ({
    x: i,
    y: r.rating,
    tip: `${r.title ?? 'Session'}: ${RATINGS[r.rating - 1].label}`,
  })),
)

const ratingLabels = computed(() => {
  const list = stats.value.ratings
  return list.length ? [short(list[0].date), short(list[list.length - 1].date)] : []
})

const series = computed(() =>
  Object.entries(METRICS)
    .map(([metric, m]) => {
      const rows = entries.value.filter((e) => e.metric === metric)
      const first = rows[0]
      const last = rows[rows.length - 1]
      return {
        metric,
        ...m,
        rows,
        last,
        change: rows.length > 1 ? last.value - first.value : null,
        points: rows.map((r) => ({
          x: parseDay(r.date).getTime(),
          y: r.value,
          tip: `${short(r.date)}: ${r.value} ${m.unit}`,
        })),
        labels: rows.length ? [short(first.date), short(last.date)] : [],
      }
    })
    .filter((s) => s.rows.length),
)

const recentEntries = computed(() => [...entries.value].reverse())

async function add() {
  error.value = ''
  fields.value = {}
  busy.value = true
  try {
    await api.addProgress({ ...form })
    form.value = null
    entries.value = (await api.progress()).progress
  } catch (e) {
    error.value = e.message
    fields.value = e.fields || {}
  } finally {
    busy.value = false
  }
}

async function remove(entry) {
  try {
    await api.deleteProgress(entry.id)
    entries.value = entries.value.filter((e) => e.id !== entry.id)
  } catch (e) {
    toast(e.message, 'bad')
  }
}
</script>

<template>
  <div v-if="loading" class="center-load">Loading…</div>
  <p v-else-if="error && !stats" class="err" role="alert">{{ error }}</p>

  <template v-else>
    <header class="page-head">
      <div>
        <h1 class="display page-title">Progress</h1>
        <Ropes />
      </div>
    </header>

    <div class="stack">
      <section class="tiles" aria-label="Your totals">
        <div class="tile"><b>{{ stats.sessions }}</b><span>Sessions</span></div>
        <div class="tile"><b>{{ stats.rounds }}</b><span>Rounds boxed</span></div>
        <div class="tile"><b>{{ (stats.minutes / 60).toFixed(1) }}</b><span>Hours</span></div>
        <div class="tile"><b>{{ stats.week_streak }}</b><span>Week streak</span></div>
      </section>

      <div class="chart-grid">
        <section class="panel">
          <p class="eyebrow">Sessions per week</p>
          <BarChart :items="weekBars" title="Sessions per week" />
        </section>
        <section class="panel">
          <p class="eyebrow">How sessions felt</p>
          <LineChart v-if="ratingPoints.length > 1" :points="ratingPoints" :y-ticks="RATING_TICKS"
            :x-labels="ratingLabels" title="Session ratings over time" color="var(--gold)" />
          <p v-else class="muted">Rate two sessions and the trend shows up here.</p>
        </section>
      </div>

      <section class="panel">
        <p class="eyebrow">Log a measurement</p>
        <form class="stack" novalidate @submit.prevent="add">
          <div class="form-grid">
            <label class="field">
              <span>Measurement</span>
              <select v-model="form.metric">
                <option v-for="(m, key) in METRICS" :key="key" :value="key">{{ m.label }} ({{ m.unit }})</option>
              </select>
            </label>
            <label class="field">
              <span>Value</span>
              <input v-model.number="form.value" type="number" inputmode="decimal" step="0.1" :aria-invalid="!!fields.value" />
              <small v-if="fields.value" class="err">{{ fields.value }}</small>
            </label>
            <label class="field">
              <span>Date</span>
              <input v-model="form.date" type="date" :max="today" :aria-invalid="!!fields.date" />
              <small v-if="fields.date" class="err">{{ fields.date }}</small>
            </label>
          </div>
          <div><button class="btn primary" :disabled="busy">Add entry</button></div>
        </form>
      </section>

      <div v-if="series.length" class="chart-grid">
        <section v-for="s in series" :key="s.metric" class="panel">
          <p class="eyebrow">{{ s.label }}</p>
          <p style="margin-bottom: 0.5rem">
            <span class="big-word">{{ s.last.value }} {{ s.unit }}</span>
            <span v-if="s.change !== null" class="muted small" style="margin-left: 0.6rem">
              {{ s.change > 0 ? '+' : '' }}{{ s.change.toFixed(1) }} since {{ s.labels[0] }}
            </span>
          </p>
          <LineChart v-if="s.points.length > 1" :points="s.points" :x-labels="s.labels" :title="`${s.label} over time`" />
        </section>
      </div>

      <details v-if="entries.length" class="about">
        <summary>All entries ({{ entries.length }})</summary>
        <ul class="plain entries" style="margin-top: 0.75rem">
          <li v-for="e in recentEntries" :key="e.id" class="small">
            <span>{{ METRICS[e.metric].label }} <span class="muted">· {{ fmtDate(e.date) }}</span></span>
            <span class="num">{{ e.value }} {{ METRICS[e.metric].unit }}</span>
            <button class="icon-btn" style="width: 36px; height: 36px" :aria-label="`Delete ${METRICS[e.metric].label} entry from ${fmtDate(e.date)}`"
              @click="remove(e)"><Icon name="trash" :size="16" /></button>
          </li>
        </ul>
      </details>
    </div>
  </template>
</template>
