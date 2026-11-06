<script setup>
defineProps({ name: { type: String, required: true }, size: { type: Number, default: 22 } })

const PATHS = {
  today: 'M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
  plan: 'M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z',
  progress: 'M4 20V4M4 20h16M8 15l3.5-4 3 2.5L20 7',
  settings: 'M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4',
  play: 'M7 4.5v15l12.5-7.5L7 4.5Z',
  pause: 'M8 5v14M16 5v14',
  next: 'M6 5l9 7-9 7V5ZM18 5v14',
  prev: 'M18 5l-9 7 9 7V5ZM6 5v14',
  close: 'M6 6l12 12M18 6 6 18',
  check: 'M5 12.5 10 17.5 19 7',
  chevron: 'M6 9l6 6 6-6',
  back: 'M15 5l-7 7 7 7',
  swap: 'M4 8h13l-3-3M20 16H7l3 3',
  sound: 'M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4ZM15.5 9a4 4 0 0 1 0 6M18 6.5a8 8 0 0 1 0 11',
  mute: 'M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4ZM16 9.5l5 5M21 9.5l-5 5',
  trash: 'M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13',
}
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="PATHS[name]" />
  </svg>
</template>
