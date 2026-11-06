<script setup>
// The profile inputs, used in pieces by the setup wizard and whole in Settings.
import { BODY_PARTS, EQUIPMENT, GOALS, LEVELS } from '../lib/format'
import ChoiceGrid from './ChoiceGrid.vue'
import PillGroup from './PillGroup.vue'

defineProps({
  form: { type: Object, required: true },
  errors: { type: Object, default: () => ({}) },
  sections: { type: Array, default: () => ['goal', 'level', 'setup', 'body'] },
})

const DAYS = [2, 3, 4, 5, 6].map((n) => ({ value: n, label: String(n) }))
const MINUTES = [30, 45, 60].map((n) => ({ value: n, label: `${n} min` }))
const WEEKS = [2, 4, 6, 8, 12].map((n) => ({ value: n, label: `${n} weeks` }))
</script>

<template>
  <ChoiceGrid v-if="sections.includes('goal')" v-model="form.goal" legend="Main goal" name="goal" :options="GOALS" />

  <ChoiceGrid v-if="sections.includes('level')" v-model="form.experience_level"
    legend="Experience" name="level" :options="LEVELS" />

  <template v-if="sections.includes('setup')">
    <ChoiceGrid v-model="form.equipment" legend="Equipment" name="equipment" :options="EQUIPMENT" />
    <label class="toggle-row">
      <input v-model="form.has_heavy_bag" type="checkbox" />
      I have a heavy bag
    </label>
    <PillGroup v-model="form.days_per_week" legend="Sessions per week" name="days" :options="DAYS" />
    <PillGroup v-model="form.session_minutes" legend="Session length" name="minutes" :options="MINUTES" />
    <PillGroup v-model="form.plan_weeks" legend="Plan length" name="weeks" :options="WEEKS" />
  </template>

  <template v-if="sections.includes('body')">
    <div class="form-grid">
      <label class="field">
        <span>Age</span>
        <input v-model.number="form.age" type="number" inputmode="numeric" min="14" max="90"
          :aria-invalid="!!errors.age" />
        <small v-if="errors.age" class="err">{{ errors.age }}</small>
      </label>
      <label class="field">
        <span>Weight (kg)</span>
        <input v-model.number="form.weight_kg" type="number" inputmode="decimal" step="0.1"
          :aria-invalid="!!errors.weight_kg" />
        <small v-if="errors.weight_kg" class="err">{{ errors.weight_kg }}</small>
      </label>
      <label class="field">
        <span>Height (cm, optional)</span>
        <input v-model.number="form.height_cm" type="number" inputmode="numeric"
          :aria-invalid="!!errors.height_cm" />
        <small v-if="errors.height_cm" class="err">{{ errors.height_cm }}</small>
      </label>
    </div>
    <fieldset>
      <legend>Anything to avoid? Injury or discomfort</legend>
      <div class="pills">
        <label v-for="p in BODY_PARTS" :key="p" class="pill">
          <input v-model="form.avoid_body_parts" type="checkbox" :value="p" />
          <span>{{ p }}</span>
        </label>
      </div>
    </fieldset>
  </template>
</template>
