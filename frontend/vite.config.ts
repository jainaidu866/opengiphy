/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/tests/**/*.test.ts'],
    setupFiles: ['src/tests/setup.ts'],
  },
  server: {
    port: 5173,
    allowedHosts: true,
    cors: true,
    proxy: {
      // The axios client uses a same-origin baseURL (''), so in dev we proxy
      // the backend's API path prefixes to the FastAPI server. (In production
      // FastAPI serves the built frontend, so no proxy is involved.)
      // These plural prefixes don't collide with the SPA routes /gif/:id,
      // /profile/:username or /upload.
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/gifs': { target: 'http://localhost:8000', changeOrigin: true },
      '/profiles': { target: 'http://localhost:8000', changeOrigin: true },
      // Serve uploaded GIFs straight from the backend in dev.
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
