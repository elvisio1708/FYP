<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import Building from '../components/Building.vue'
import Icon from '../components/Icon.vue'
import Ropes from '../components/Ropes.vue'
import { fmtDate, intensityWords, isoToday, parseDay, relativeDay } from '../lib/format'
import { nextSession } from '../lib/schedule'
import { store, toast } from '../lib/store'

const plan = ref(null)
const stats = ref(null)
const loading = ref(true)
const building = ref(false)
const error = ref('')
const today = isoToday()

onMounted(async () => {
  try {
    const [p, s] = await Promise.all([api.currentPlan(), api.stats()])
    plan.value = p.plan
    stats.value = s
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

async function newPlan() {
  building.value = true
  try {
    plan.value = (await api.createPlan()).plan
  } catch (e) {
    toast(e.message, 'bad')
  } finally {
    building.value = false
  }
}

const next = computed(() => nextSession(plan.value?.sessions ?? [], today))
const planFinished = computed(() => plan.value && !next.value)
const overdue = computed(() => next.value && next.value.scheduled_for < today)
const restDay = computed(() => next.value && next.value.scheduled_for > today)

const heroLabel = computed(() => {
  if (overdue.value) return `Catch up · planned for ${fmtDate(next.value.scheduled_for)}`
  if (restDay.value) return `Rest day · next up ${relativeDay(next.value.scheduled_for, today).toLowerCase()}`
  return `Today · Week ${next.value.week}`
})

const roundCount = computed(() =>
  (next.value?.exercises ?? []).filter((e) => e.kind === 'boxing').reduce((sum, e) => sum + (e.circuit ? 0 : e.sets), 0),
)

const week = computed(() => {
  const base = parseDay(today)
  const monday = new Date(base)
  monday.setDate(base.getDate() - ((base.getDay() + 6) % 7))
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(monday)
    day.setDate(monday.getDate() + i)
    const iso = isoToday(day)
    const session = plan.value?.sessions.find((s) => s.scheduled_for === iso)
    let state = null
    if (session) state = session.completed ? 'done' : iso < today ? 'missed' : 'planned'
    return {
      iso,
      session,
      state,
      letter: day.toLocaleDateString(undefined, { weekday: 'narrow' }),
      date: day.getDate(),
    }
  })
})

const gaugeLeft = computed(() => `${((stats.value.next_plan_intensity - 0.8) / 0.4) * 100}%`)
const greeting = computed(() => {
  const hour = new Date().getHours()
  return hour < 12 ? 'Morning' : hour < 18 ? 'Afternoon' : 'Evening'
})
</script>

<template>
  <Building v-if="building" />
  <div v-if="loading" class="center-load">Loading…</div>
  <p v-else-if="error" class="err" role="alert">{{ error }}</p>

  <template v-else>
    <header class="page-head">
      <div>
        <h1 class="display page-title">{{ greeting }}, {{ store.user?.username }}</h1>
        <Ropes />
      </div>
    </header>

    <div class="today-grid">
      <section v-if="!plan" class="hero">
        <p class="eyebrow">No plan yet</p>
        <h2 class="display">Let's build one</h2>
        <div class="actions"><button class="btn bone big" @click="newPlan">Build my plan</button></div>
      </section>

      <section v-else-if="planFinished" class="hero">
        <p class="eyebrow">Plan complete</p>
        <h2 class="display">All {{ plan.sessions_total }} sessions done</h2>
        <p class="meta"><span>Next plan: {{ intensityWords(stats.next_plan_intensity).toLowerCase() }}</span></p>
        <div class="actions"><button class="btn bone big" @click="newPlan">Build the next one</button></div>
      </section>

      <section v-else class="hero" :class="{ calm: restDay }">
        <p class="eyebrow">{{ heroLabel }}</p>
        <h2 class="display">{{ next.title }}</h2>
        <p class="meta">
          <span>{{ next.focus }}</span>
          <span>~{{ next.duration_minutes }} min</span>
          <span v-if="roundCount">{{ roundCount }} rounds</span>
        </p>
        <div class="actions">
          <RouterLink class="btn big" :class="restDay ? 'primary' : 'bone'" :to="`/session/${next.id}/go`">
            <Icon name="play" /> {{ restDay ? 'Train anyway' : 'Start session' }}
          </RouterLink>
          <RouterLink class="link" :to="`/session/${next.id}`">See what's in it</RouterLink>
        </div>
      </section>

      <div class="stack">
        <section v-if="plan" class="panel">
          <p class="eyebrow">This week</p>
          <div class="weekstrip">
            <component :is="d.session ? RouterLink : 'div'" v-for="d in week" :key="d.iso" class="day"
              :class="{ today: d.iso === today }" :to="d.session ? `/session/${d.session.id}` : undefined"
              :aria-label="d.session ? `${fmtDate(d.iso)}: ${d.session.title}, ${d.state}` : undefined">
              <small>{{ d.letter }}</small>
              <b>{{ d.date }}</b>
              <span v-if="d.state" class="pip" :class="d.state">
                <Icon v-if="d.state === 'done'" name="check" :size="12" />
              </span>
              <span v-else class="pip"></span>
            </component>
          </div>
        </section>

        <section class="tiles" aria-label="Your totals">
          <div class="tile"><b>{{ stats.week_streak }}</b><span>Week streak</span></div>
          <div class="tile"><b>{{ stats.sessions }}</b><span>Sessions</span></div>
          <div class="tile"><b>{{ stats.rounds }}</b><span>Rounds</span></div>
          <div class="tile"><b>{{ (stats.minutes / 60).toFixed(1) }}</b><span>Hours</span></div>
        </section>
      </div>

      <section class="panel">
        <p class="eyebrow">Your next plan</p>
        <p class="big-word">{{ intensityWords(stats.next_plan_intensity) }}</p>
        <div class="gauge"><i :style="{ left: gaugeLeft }"></i></div>
        <div class="gauge-ends"><span>Easier</span><span>Harder</span></div>
        <p class="muted small" style="margin-top: 0.75rem">
          <template v-if="stats.average_rating">
            Your recent sessions average {{ stats.average_rating }} out of 5, where 3 is about right.
          </template>
          <template v-else>Rate your sessions and the next plan adjusts to match.</template>
        </p>
      </section>
    </div>
  </template>
</template>
