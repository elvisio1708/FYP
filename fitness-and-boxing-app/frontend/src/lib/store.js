import { reactive } from 'vue'
import { api } from '../api'

// App-wide state: who is logged in, their profile, toasts and the confirm dialog.
export const store = reactive({
  ready: false,
  user: null,
  profile: null,
  toasts: [],
  confirm: null,
})

let booting = null

export function boot() {
  booting ??= (async () => {
    try {
      store.user = (await api.me()).user
      store.profile = (await api.profile()).profile
    } catch {
      store.user = null
    }
    store.ready = true
  })()
  return booting
}

export async function signedIn(user) {
  store.user = user
  store.profile = (await api.profile()).profile
}

export function signedOut() {
  store.user = null
  store.profile = null
}

let toastId = 0

export function toast(message, tone = 'ok') {
  const id = ++toastId
  store.toasts.push({ id, message, tone })
  setTimeout(() => {
    store.toasts = store.toasts.filter((t) => t.id !== id)
  }, 4200)
}

// Resolves true or false. Replaces window.confirm so it matches the app.
export function confirmDialog(options) {
  return new Promise((resolve) => {
    store.confirm = {
      confirmLabel: 'Confirm',
      cancelLabel: 'Cancel',
      danger: false,
      ...options,
      resolve(value) {
        store.confirm = null
        resolve(value)
      },
    }
  })
}
