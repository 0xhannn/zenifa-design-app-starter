import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built assets land in static/ so FastAPI can serve them
export default defineConfig({
  plugins: [react()],
  base: '/poll-app/',
  build: {
    outDir: '../static/poll-app',
    emptyOutDir: true,
  },
  server: {
    port: 5179,
    proxy: {
      '/api': 'http://127.0.0.1:3888',
    },
  },
})
