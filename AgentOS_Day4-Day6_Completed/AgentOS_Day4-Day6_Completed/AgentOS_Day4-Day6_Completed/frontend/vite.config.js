import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/task': 'http://127.0.0.1:8000',
      '/history': 'http://127.0.0.1:8000',
      '/metrics': 'http://127.0.0.1:8000',
      '/blocked': 'http://127.0.0.1:8000',
      '/scheduler': 'http://127.0.0.1:8000',
      '/results': 'http://127.0.0.1:8000',
      '/stream': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: '../backend/static/web',
    emptyOutDir: true,
  },
})
