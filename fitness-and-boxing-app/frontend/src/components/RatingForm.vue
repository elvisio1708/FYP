<script setup>
import { ref } from 'vue'
import { RATINGS } from '../lib/format'

defineProps({ busy: Boolean, submitLabel: { type: String, default: 'Log session' } })
const emit = defineEmits(['submit'])

const rating = ref(3)
const notes = ref('')
</script>

<template>
  <form class="stack" @submit.prevent="emit('submit', { rating, notes })">
    <fieldset>
      <legend>How did it feel?</legend>
      <div class="rating">
        <label v-for="r in RATINGS" :key="r.value">
          <input v-model.number="rating" type="radio" name="rating" :value="r.value" />
          <span>{{ r.label }}</span>
        </label>
      </div>
    </fieldset>
    <label class="field">
      <span>Notes (optional)</span>
      <textarea v-model="notes" rows="2" maxlength="1000"></textarea>
    </label>
    <button class="btn primary big block" :disabled="busy">{{ busy ? 'Saving…' : submitLabel }}</button>
  </form>
</template>
