<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import Building from '../components/Building.vue'
import ProfileFields from '../components/ProfileFields.vue'
import Ropes from '../components/Ropes.vue'
import { confirmDialog, signedOut, store, toast } from '../lib/store'

const router = useRouter()

const form = reactive({ ...store.profile, avoid_body_parts: [...(store.profile?.avoid_body_parts ?? [])] })
const errors = ref({})
const saving = ref(false)
const saved = ref(false)
const building = ref(false)

const passwords = reactive({ current_password: '', new_password: '' })
const passwordErrors = ref({})
const passwordError = ref('')
const removing = ref(false)
const deletePassword = ref('')
const deleteError = ref('')

async function save() {
  errors.value = {}
  saving.value = true
  try {
    const { profile } = await api.saveProfile({ ...form, height_cm: form.height_cm || null })
    store.profile = profile
    saved.value = true
    toast('Profile saved.')
  } catch (e) {
    errors.value = e.fields || {}
    toast(e.message, 'bad')
  } finally {
    saving.value = false
  }
}

async function rebuild() {
  building.value = true
  try {
    await api.createPlan()
    toast('New plan ready.')
    router.push('/plan')
  } catch (e) {
    toast(e.message, 'bad')
    building.value = false
  }
}

async function changePassword() {
  passwordErrors.value = {}
  passwordError.value = ''
  try {
    await api.changePassword({ ...passwords })
    passwords.current_password = ''
    passwords.new_password = ''
    toast('Password updated.')
  } catch (e) {
    passwordErrors.value = e.fields || {}
    if (!e.fields?.new_password) passwordError.value = e.message
  }
}

async function logout() {
  try {
    await api.logout()
  } finally {
    signedOut()
    router.replace('/login')
  }
}

async function deleteAccount() {
  deleteError.value = ''
  const ok = await confirmDialog({
    title: 'Delete your account?',
    body: 'Your plans, ratings and measurements are removed for good. This cannot be undone.',
    confirmLabel: 'Delete everything',
    danger: true,
  })
  if (!ok) return
  try {
    await api.deleteAccount({ password: deletePassword.value })
    signedOut()
    router.replace('/login')
  } catch (e) {
    deleteError.value = e.message
  }
}
</script>

<template>
  <Building v-if="building" />

  <header class="page-head">
    <div>
      <h1 class="display page-title">Settings</h1>
      <Ropes />
    </div>
    <button class="btn" @click="logout">Log out</button>
  </header>

  <div class="stack">
    <form class="panel stack" novalidate @submit.prevent="save">
      <p class="eyebrow">Training profile</p>
      <ProfileFields :form="form" :errors="errors" />
      <div class="dialog-actions" style="justify-content: flex-start; margin-top: 0">
        <button class="btn primary" :disabled="saving">{{ saving ? 'Saving…' : 'Save profile' }}</button>
        <button v-if="saved" type="button" class="btn" @click="rebuild">Build a new plan with this</button>
      </div>
      <p class="muted small">Changes apply to your next plan, not the one you're on.</p>
    </form>

    <form class="panel stack" novalidate @submit.prevent="changePassword">
      <p class="eyebrow">Password</p>
      <div class="form-grid">
        <label class="field">
          <span>Current password</span>
          <input v-model="passwords.current_password" type="password" autocomplete="current-password" />
        </label>
        <label class="field">
          <span>New password</span>
          <input v-model="passwords.new_password" type="password" autocomplete="new-password"
            :aria-invalid="!!passwordErrors.new_password" />
          <small v-if="passwordErrors.new_password" class="err">{{ passwordErrors.new_password }}</small>
        </label>
      </div>
      <p v-if="passwordError" class="err" role="alert">{{ passwordError }}</p>
      <div><button class="btn">Change password</button></div>
    </form>

    <section class="panel stack">
      <p class="eyebrow">Delete account</p>
      <p class="muted small">Signed in as {{ store.user?.username }} ({{ store.user?.email }}).</p>
      <button v-if="!removing" class="btn danger" style="justify-self: start" @click="removing = true">Delete my account</button>
      <form v-else class="stack" novalidate @submit.prevent="deleteAccount">
        <label class="field" style="max-width: 320px">
          <span>Enter your password to confirm</span>
          <input v-model="deletePassword" type="password" autocomplete="current-password" />
        </label>
        <p v-if="deleteError" class="err" role="alert">{{ deleteError }}</p>
        <div><button class="btn danger">Delete my account</button></div>
      </form>
    </section>

    <p class="disclaimer">
      General fitness guidance only, not medical advice. If you have an injury or health condition, check with a
      doctor before starting a new programme. Learn boxing technique with a qualified coach; this app does not
      include sparring.
    </p>
  </div>
</template>
