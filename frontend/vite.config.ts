import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  root: '.',
  build: { outDir: 'dist' },
  server: {
    proxy: {
      '/run': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/garage': 'http://localhost:8000',
      '/inventory': 'http://localhost:8000',
      '/profile': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/test': 'http://localhost:8000',
    },
  },
})
