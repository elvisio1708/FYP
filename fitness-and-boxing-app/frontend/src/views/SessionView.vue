<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import Icon from '../components/Icon.vue'
import RatingForm from '../components/RatingForm.vue'
import { PUNCHES, difficultyLabel, fmtDate, mmss, prescription, relativeDay } from '../lib/format'
import { confirmDialog, toast } from '../lib/store'

const props = defineProps({ id: { type: String, required: true } })

const plan = ref(null)
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const swapping = ref(null)
const logging = ref(false)

onMounted(async () => {
  try {
    plan.value = (await api.currentPlan()).plan
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

const session = computed(() => plan.value?.sessions.find((s) => s.id === Number(props.id)) ?? null)

const groups = computed(() => {
  const list = session.value?.exercises ?? []
  const of = (...kinds) => list.filter((e) => kinds.includes(e.kind))
  const circuit = list.find((e) => e.circuit)
  return [
    { label: 'Warm-up', items: of('warmup') },
    {
      label: circuit ? `Circuit · ${circuit.sets} rounds, stations in order` : 'Main work',
      items: of('boxing', 'gym'),
    },
    { label: 'Cool-down', items: of('cooldown') },
  ].filter((g) => g.items.length)
})

const showPunches = computed(() => ['boxing_technique', 'boxing_bag'].includes(session.value?.kind))

const doLabel = (e) => (e.circuit ? `${mmss(e.duration_seconds)} on` : prescription(e))
const cleanName = (e) => e.name.replace(/^Circuit: /, '')

async function swap(exercise) {
  swapping.value = exercise.id
  try {
    const res = await api.swapExercise(exercise.id)
    plan.value = res.plan
    toast(`Swapped in ${res.replacement} for the rest of this plan.`)
  } catch (e) {
    toast(e.message, 'bad')
  } finally {
    swapping.value = null
  }
}

async function log(values) {
  busy.value = true
  try {
    await api.completeSession(session.value.id, values)
    session.value.completed = true
    logging.value = false
    toast('Session logged.')
  } catch (e) {
    toast(e.message, 'bad')
  } finally {
    busy.value = false
  }
}

async function undo() {
  const ok = await confirmDialog({
    title: 'Reopen this session?',
    body: 'Its rating is removed and it no longer counts towards your stats.',
    confirmLabel: 'Reopen',
  })
  if (!ok) return
  try {
    await api.undoSession(session.value.id)
    session.value.completed = false
    toast('Session reopened.')
  } catch (e) {
    toast(e.message, 'bad')
  }
}
</script>

<template>
  <div v-if="loading" class="center-load">Loading…</div>
  <p v-else-if="error" class="err" role="alert">{{ error }}</p>

  <div v-else-if="!session" class="stack">
    <h1 class="display page-title">Session not found</h1>
    <p class="muted">It may belong to an older plan.</p>
    <RouterLink class="btn" to="/plan" style="justify-self: start">Back to the plan</RouterLink>
  </div>

  <article v-else class="stack">
    <div>
      <RouterLink class="crumb" to="/plan"><Icon name="back" :size="18" /> The plan</RouterLink>
      <p class="eyebrow">
        Week {{ session.week }} · {{ relativeDay(session.scheduled_for) }} · {{ fmtDate(session.scheduled_for) }}
      </p>
      <h1 class="display page-title">{{ session.title }}</h1>
      <p class="muted">{{ session.focus }} · about {{ session.duration_minutes }} minutes</p>
    </div>

    <section v-for="g in groups" :key="g.label">
      <p class="eyebrow" style="margin-bottom: 0.5rem">{{ g.label }}</p>
      <div class="ex-group">
        <div v-for="e in g.items" :key="e.id" class="ex">
          <div class="ex-top">
            <b>{{ cleanName(e) }}</b>
            <span class="ex-do">{{ doLabel(e) }}</span>
          </div>
          <p v-if="e.description">{{ e.description }}</p>
          <div v-if="e.kind === 'gym' || (e.rest_seconds && !e.circuit)" class="ex-meta">
            <span v-if="e.kind === 'gym'">{{ e.body_part }} · {{ e.equipment }}</span>
            <span v-if="e.rest_seconds">Rest {{ e.rest_seconds }}s</span>
            <span v-if="e.match_score" class="fit" :title="`Predicted difficulty ${e.difficulty?.toFixed(2)} on a 0 to 2 scale`">
              {{ difficultyLabel(e.difficulty) }} · {{ Math.round(e.match_score * 100) }}% match
            </span>
            <button v-if="e.kind === 'gym' && !session.completed" class="link small" :disabled="swapping === e.id"
              @click="swap(e)">
              {{ swapping === e.id ? 'Swapping…' : 'Swap' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section v-if="showPunches" class="panel">
      <p class="eyebrow">Punch numbers</p>
      <div class="punches small">
        <span v-for="[n, name] in PUNCHES" :key="n"><b>{{ n }}</b>{{ name }}</span>
      </div>
    </section>

    <section v-if="logging" class="panel"><RatingForm :busy="busy" @submit="log" /></section>

    <div v-if="session.completed" class="sticky-start">
      <span class="btn" style="border-color: var(--gold); color: var(--gold); cursor: default">
        <Icon name="check" /> Done
      </span>
      <button class="link" @click="undo">Reopen session</button>
    </div>
    <div v-else class="sticky-start">
      <RouterLink class="btn primary big" :to="`/session/${session.id}/go`"><Icon name="play" /> Start session</RouterLink>
      <button v-if="!logging" class="btn" style="background: var(--ink)" @click="logging = true">Already done it</button>
    </div>
  </article>
</template>
