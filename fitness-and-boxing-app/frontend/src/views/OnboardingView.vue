<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import Building from '../components/Building.vue'
import ProfileFields from '../components/ProfileFields.vue'
import { store } from '../lib/store'

const router = useRouter()

const STEPS = [
  { section: 'goal', title: "What's the goal?", sub: 'This sets the shape of your week.' },
  { section: 'level', title: 'How much have you trained?', sub: 'Be honest. The plan moves up as you do.' },
  { section: 'setup', title: 'What are you working with?', sub: 'Sessions are built to fit, and never run over.' },
  { section: 'body', title: 'Last thing: you', sub: 'Anything you mark to avoid is left out of your plan.' },
]

const form = reactive({
  goal: 'boxing',
  experience_level: 'beginner',
  equipment: 'bodyweight',
  has_heavy_bag: false,
  days_per_week: 3,
  session_minutes: 45,
  plan_weeks: 4,
  age: null,
  weight_kg: null,
  height_cm: null,
  avoid_body_parts: [],
})
const step = ref(0)
const building = ref(false)
const error = ref('')
const errors = ref({})
const current = computed(() => STEPS[step.value])
const isLast = computed(() => step.value === STEPS.length - 1)

async function next() {
  if (!isLast.value) {
    step.value++
    return
  }
  error.value = ''
  errors.value = {}
  building.value = true
  try {
    const { profile } = await api.saveProfile({ ...form, height_cm: form.height_cm || null })
    store.profile = profile
    await api.createPlan()
    router.replace('/')
  } catch (e) {
    error.value = e.message
    errors.value = e.fields || {}
    building.value = false
  }
}
</script>

<template>
  <Building v-if="building" />

  <main v-else class="wizard">
    <div class="wizard-steps" role="progressbar" :aria-valuenow="step + 1" aria-valuemin="1" :aria-valuemax="STEPS.length"
      aria-label="Setup progress">
      <i v-for="(s, n) in STEPS" :key="s.section" :class="{ on: n <= step }"></i>
    </div>

    <div>
      <p class="eyebrow">Step {{ step + 1 }} of {{ STEPS.length }}</p>
      <h1 class="display page-title">{{ current.title }}</h1>
      <p class="muted">{{ current.sub }}</p>
    </div>

    <form class="wizard-body" novalidate @submit.prevent="next">
      <ProfileFields :form="form" :errors="errors" :sections="[current.section]" />
      <p v-if="error" class="err" role="alert">{{ error }}</p>

      <div class="wizard-nav">
        <button v-if="step" type="button" class="btn" @click="step--">Back</button>
        <span v-else></span>
        <button class="btn primary big">{{ isLast ? 'Build my plan' : 'Continue' }}</button>
      </div>
    </form>
  </main>
</template>
