import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In development the Vue app runs on :5173 and proxies /api to Flask on :5000,
// so the browser sees one origin and the session cookie just works.
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
