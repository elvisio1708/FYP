import { createRouter, createWebHistory } from 'vue-router'
import { boot, store } from './lib/store'

const routes = [
  { path: '/login', component: () => import('./views/AuthView.vue'), meta: { bare: true, public: true } },
  { path: '/welcome', component: () => import('./views/OnboardingView.vue'), meta: { bare: true } },
  { path: '/', component: () => import('./views/TodayView.vue') },
  { path: '/plan', component: () => import('./views/PlanView.vue') },
  { path: '/session/:id', component: () => import('./views/SessionView.vue'), props: true },
  { path: '/session/:id/go', component: () => import('./views/WorkoutView.vue'), props: true, meta: { bare: true } },
  { path: '/progress', component: () => import('./views/ProgressView.vue') },
  { path: '/settings', component: () => import('./views/SettingsView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  await boot()
  if (!store.user) return to.meta.public ? true : '/login'
  if (to.meta.public) return '/'
  if (!store.profile && to.path !== '/welcome') return '/welcome'
  return true
})
