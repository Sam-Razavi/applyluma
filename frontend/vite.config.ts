/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { sentryVitePlugin } from '@sentry/vite-plugin'

const sentryEnabled = Boolean(process.env.SENTRY_AUTH_TOKEN)
const isSsrBuild = process.argv.includes('--ssr')

export default defineConfig({
  plugins: [
    react(),
    ...(sentryEnabled
      ? [
          sentryVitePlugin({
            org: process.env.SENTRY_ORG ?? 'applyluma',
            project: process.env.SENTRY_PROJECT ?? 'applyluma-frontend',
          }),
        ]
      : []),
  ],
  build: {
    sourcemap: sentryEnabled,
    rollupOptions: {
      output: isSsrBuild
        ? undefined
        : {
            // Carve the largest, rarely-changing libs into their own long-lived
            // cache chunks so app-code deploys don't invalidate them.
            manualChunks: {
              'react-vendor': ['react', 'react-dom', 'react-router-dom'],
              charts: ['recharts'],
              motion: ['framer-motion'],
            },
          },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
