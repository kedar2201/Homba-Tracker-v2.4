import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  root: './',
  base: './',
  plugins: [
    react(),
  ],
  server: {
    port: 9001,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-utils': ['axios', 'date-fns', 'clsx', 'tailwind-merge'],
          'vendor-viz': ['recharts', 'framer-motion'],
          'vendor-export': ['xlsx', 'jspdf', 'jspdf-autotable', 'file-saver'],
        }
      }
    },
    chunkSizeWarningLimit: 1000,
  }
})
