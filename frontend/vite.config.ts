import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// In development the Flask API runs on :5001 (macOS reserves :5000 for AirPlay).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:5001' },
  },
  test: { environment: 'node' },
})
