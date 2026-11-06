<script setup>
// Radio group rendered as cards. `options` is { value: { label, blurb } }.
defineProps({
  legend: { type: String, required: true },
  name: { type: String, required: true },
  options: { type: Object, required: true },
})
const model = defineModel({ type: String })
</script>

<template>
  <fieldset>
    <legend>{{ legend }}</legend>
    <div class="choices">
      <label v-for="(o, value) in options" :key="value" class="choice">
        <input v-model="model" type="radio" :name="name" :value="value" />
        <div><b>{{ o.label }}</b><small>{{ o.blurb }}</small></div>
      </label>
    </div>
  </fieldset>
</template>
