<script setup>
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import ConfirmDialog from './components/ConfirmDialog.vue'
import Icon from './components/Icon.vue'
import { store } from './lib/store'

const route = useRoute()
const bare = computed(() => route.meta.bare || route.meta.public)

const NAV = [
  { to: '/', label: 'Today', icon: 'today' },
  { to: '/plan', label: 'Plan', icon: 'plan' },
  { to: '/progress', label: 'Progress', icon: 'progress' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
]
</script>

<template>
  <div v-if="!store.ready" class="center-load" style="min-height: 100vh">Loading…</div>

  <RouterView v-else-if="bare" />

  <template v-else>
    <aside class="rail">
      <RouterLink to="/" class="logo">Seconds<span>Out</span></RouterLink>
      <nav aria-label="Main">
        <RouterLink v-for="n in NAV" :key="n.to" :to="n.to"><Icon :name="n.icon" /> {{ n.label }}</RouterLink>
      </nav>
      <p class="who muted small">{{ store.user?.username }}</p>
    </aside>

    <div class="shell">
      <main class="page"><RouterView /></main>
    </div>

    <nav class="tabbar" aria-label="Main">
      <RouterLink v-for="n in NAV" :key="n.to" :to="n.to"><Icon :name="n.icon" /> {{ n.label }}</RouterLink>
    </nav>
  </template>

  <div class="toasts" aria-live="polite">
    <div v-for="t in store.toasts" :key="t.id" class="toast" :class="{ bad: t.tone === 'bad' }">{{ t.message }}</div>
  </div>
  <ConfirmDialog />
</template>
