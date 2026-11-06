<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { signedIn } from '../lib/store'

const router = useRouter()
const mode = ref('login')
const form = reactive({ username: '', email: '', password: '' })
const error = ref('')
const fields = ref({})
const busy = ref(false)

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
  fields.value = {}
}

async function submit() {
  error.value = ''
  fields.value = {}
  busy.value = true
  try {
    const res = mode.value === 'login'
      ? await api.login({ username: form.username, password: form.password })
      : await api.register({ ...form })
    await signedIn(res.user)
    router.replace('/')
  } catch (e) {
    error.value = e.message
    fields.value = e.fields || {}
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth">
    <section class="auth-poster">
      <h1 class="display">Seconds<br />Out.</h1>
      <p>Boxing and fitness plans that adapt to how every session felt.</p>
    </section>

    <main class="auth-form">
      <div class="logo auth-logo">Seconds<span>Out</span></div>
      <div>
        <h2 class="display page-title">{{ mode === 'login' ? 'Log in' : 'Get started' }}</h2>
        <p class="muted">
          {{ mode === 'login' ? 'Your next round is waiting.' : 'A plan built around your goal, level and kit.' }}
        </p>
      </div>

      <form novalidate @submit.prevent="submit">
        <label class="field">
          <span>Username</span>
          <input v-model.trim="form.username" autocomplete="username" :aria-invalid="!!fields.username" />
          <small v-if="fields.username" class="err">{{ fields.username }}</small>
        </label>
        <label v-if="mode === 'register'" class="field">
          <span>Email</span>
          <input v-model.trim="form.email" type="email" autocomplete="email" :aria-invalid="!!fields.email" />
          <small v-if="fields.email" class="err">{{ fields.email }}</small>
        </label>
        <label class="field">
          <span>Password</span>
          <input v-model="form.password" type="password" :aria-invalid="!!fields.password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" />
          <small v-if="fields.password" class="err">{{ fields.password }}</small>
          <small v-else-if="mode === 'register'" class="muted">At least 8 characters.</small>
        </label>

        <p v-if="error && !Object.keys(fields).length" class="err" role="alert">{{ error }}</p>

        <button class="btn primary big block" :disabled="busy">
          {{ busy ? 'One moment…' : mode === 'login' ? 'Log in' : 'Create account' }}
        </button>
      </form>

      <button type="button" class="link" style="justify-self: start; align-self: flex-start" @click="switchMode">
        {{ mode === 'login' ? 'New here? Create an account' : 'Already have an account? Log in' }}
      </button>
    </main>
  </div>
</template>
