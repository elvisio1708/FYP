<script setup>
import { ref, watch, nextTick } from 'vue'
import { store } from '../lib/store'

const el = ref(null)

watch(
  () => store.confirm,
  async (value) => {
    await nextTick()
    if (value) el.value?.showModal()
    else if (el.value?.open) el.value.close()
  },
)
</script>

<template>
  <dialog ref="el" aria-labelledby="confirm-title" @cancel.prevent="store.confirm?.resolve(false)">
    <template v-if="store.confirm">
      <h2 id="confirm-title" class="display section-title">{{ store.confirm.title }}</h2>
      <p v-if="store.confirm.body">{{ store.confirm.body }}</p>
      <div class="dialog-actions">
        <button class="btn" @click="store.confirm.resolve(false)">{{ store.confirm.cancelLabel }}</button>
        <button class="btn" :class="store.confirm.danger ? 'danger' : 'primary'" @click="store.confirm.resolve(true)">
          {{ store.confirm.confirmLabel }}
        </button>
      </div>
    </template>
  </dialog>
</template>
