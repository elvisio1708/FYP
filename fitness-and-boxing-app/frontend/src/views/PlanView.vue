<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import Building from '../components/Building.vue'
import Icon from '../components/Icon.vue'
import Ropes from '../components/Ropes.vue'
import { GOALS, LEVELS, fmtDate, isoToday } from '../lib/format'
import { currentWeek, isMissed } from '../lib/schedule'
import { confirmDialog, toast } from '../lib/store'

const plan = ref(null)
const history = ref([])
const loading = ref(true)
const building = ref(false)
const error = ref('')
const today = isoToday()

onMounted(async () => {
  try {
    const [p, list] = await Promise.all([api.currentPlan(), api.plans()])
    plan.value = p.plan
    history.value = list.plans.filter((x) => x.status !== 'active')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

const weeks = computed(() => {
  const byWeek = new Map()
  for (const s of plan.value?.sessions ?? []) {
    if (!byWeek.has(s.week)) byWeek.set(s.week, [])
    byWeek.get(s.week).push(s)
  }
  const groups = [...byWeek].map(([week, sessions]) => ({
    week,
    sessions,
    done: sessions.filter((s) => s.completed).length,
  }))
  const current = currentWeek(plan.value?.sessions ?? [], plan.value?.start_date, today)
  return groups.map((g) => ({ ...g, current: g.week === current }))
})

const percent = computed(() =>
  plan.value?.sessions_total ? Math.round((plan.value.sessions_completed / plan.value.sessions_total) * 100) : 0,
)

async function generate() {
  if (plan.value) {
    const ok = await confirmDialog({
      title: 'Build a new plan?',
      body: 'Your current plan is archived. Finished sessions still count towards your stats.',
      confirmLabel: 'Build new plan',
    })
    if (!ok) return
  }
  building.value = true
  try {
    plan.value = (await api.createPlan()).plan
    history.value = (await api.plans()).plans.filter((x) => x.status !== 'active')
    toast('New plan ready.')
  } catch (e) {
    toast(e.message, 'bad')
  } finally {
    building.value = false
  }
}

const isBoxing = (s) => s.kind.startsWith('boxing')
</script>

<template>
  <Building v-if="building" />
  <div v-if="loading" class="center-load">Loading…</div>
  <p v-else-if="error" class="err" role="alert">{{ error }}</p>

  <template v-else>
    <header class="page-head">
      <div>
        <h1 class="display page-title">The plan</h1>
        <Ropes />
      </div>
      <button class="btn" @click="generate">{{ plan ? 'New plan' : 'Build my plan' }}</button>
    </header>

    <p v-if="!plan" class="muted">No plan yet. Build one and it shows up here, week by week.</p>

    <div v-else class="stack">
      <section class="panel">
        <p class="eyebrow">
          {{ GOALS[plan.goal].label }} · {{ LEVELS[plan.experience_level].label }} ·
          {{ plan.weeks }} weeks · {{ plan.days_per_week }} a week
        </p>
        <div class="bar" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100"
          aria-label="Plan progress"><i :style="{ width: `${percent}%` }"></i></div>
        <p class="muted small" style="margin-top: 0.5rem">
          {{ plan.sessions_completed }} of {{ plan.sessions_total }} sessions done
        </p>
        <ul v-if="plan.notes.length" class="plain muted small" style="margin-top: 0.75rem">
          <li v-for="n in plan.notes" :key="n">{{ n }}</li>
        </ul>
      </section>

      <div>
        <details v-for="w in weeks" :key="w.week" class="week" :open="w.current">
          <summary>
            <span>
              <span class="display">Week {{ w.week }}</span>
              <span v-if="w.current" class="tag">Now</span>
            </span>
            <span class="row-end muted small" style="display: flex; gap: 0.6rem; align-items: center">
              {{ w.done }}/{{ w.sessions.length }} <Icon name="chevron" :size="18" />
            </span>
          </summary>
          <div class="rows">
            <RouterLink v-for="s in w.sessions" :key="s.id" :to="`/session/${s.id}`" class="row"
              :class="[isBoxing(s) ? 'boxing' : 'gym', { done: s.completed }]">
              <span class="when">
                <b>{{ fmtDate(s.scheduled_for, { weekday: 'short' }) }}</b>
                {{ fmtDate(s.scheduled_for, { day: 'numeric', month: 'short' }) }}
              </span>
              <span class="what">
                <b>{{ s.title }}</b>
                <small>{{ s.focus }}</small>
              </span>
              <span class="state">
                <template v-if="s.completed"><Icon class="check" name="check" :size="20" /><span class="sr-only">Done</span></template>
                <template v-else-if="isMissed(s, today)">Missed</template>
                <template v-else>{{ s.duration_minutes }} min</template>
              </span>
            </RouterLink>
          </div>
        </details>
      </div>

      <section v-if="history.length" class="panel">
        <p class="eyebrow">Past plans</p>
        <ul class="plain">
          <li v-for="h in history" :key="h.id" class="small">
            {{ GOALS[h.goal].label }}, {{ h.weeks }} weeks:
            <span class="muted">{{ h.sessions_completed }} of {{ h.sessions_total }} done · started {{ fmtDate(h.created_at.slice(0, 10)) }}</span>
          </li>
        </ul>
      </section>

      <details class="about">
        <summary>How this plan was built</summary>
        <ol>
          <li>Your goal and days per week pick the shape of each week.</li>
          <li>Boxing rounds are worked out from your session length, so they fit the time you have.</li>
          <li>
            Gym exercises come from a library of about 2,900. A model trained on coaching rules scores how hard
            each one is, and each is then ranked on goal fit, level fit and rating. Your kit and any body parts
            you avoid are hard rules, and beginners never get the hardest exercises.
          </li>
          <li>Your last six session ratings set the intensity of the next plan, from 20% easier to 20% harder.</li>
        </ol>
      </details>
    </div>
  </template>
</template>
