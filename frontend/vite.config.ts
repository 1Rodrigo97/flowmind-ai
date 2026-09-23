import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    // 5173 is Vite's default; using 5180 avoids clashing with other local projects.
    port: 5180,
  },
})
