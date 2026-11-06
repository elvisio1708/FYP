<script setup>
// Single-series column chart in plain HTML so the columns can be hovered and
// labelled without any scaling maths. `items` is [{ key, label, value, tip }].
import { computed, ref } from 'vue'

const props = defineProps({
  items: { type: Array, required: true },
  title: { type: String, required: true },
})

const hover = ref(null)
const peak = computed(() => Math.max(1, ...props.items.map((i) => i.value)))
</script>

<template>
  <div class="bars" role="img" :aria-label="`${title}: ${items.map((i) => `${i.label} ${i.value}`).join(', ')}`">
    <div v-for="(item, n) in items" :key="item.key" class="col" :class="{ zero: !item.value }"
      @pointerenter="hover = n" @pointerleave="hover = null">
      <span v-if="hover === n" class="tip" style="left: 50%">{{ item.tip }}</span>
      <span class="val">{{ item.value || '' }}</span>
      <i :style="{ height: `${(item.value / peak) * 118}px` }"></i>
      <small>{{ item.label }}</small>
    </div>
  </div>
</template>
