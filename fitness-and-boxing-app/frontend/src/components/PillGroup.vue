<script setup>
// Single-choice row of small options. `options` is [{ value, label }].
defineProps({
  legend: { type: String, required: true },
  name: { type: String, required: true },
  options: { type: Array, required: true },
})
const model = defineModel({ type: Number })
</script>

<template>
  <fieldset>
    <legend>{{ legend }}</legend>
    <div class="pills">
      <label v-for="o in options" :key="o.value" class="pill">
        <input v-model="model" type="radio" :name="name" :value="o.value" />
        <span>{{ o.label }}</span>
      </label>
    </div>
  </fieldset>
</template>
