import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '..',  // Load .env from project root

  // Performance optimizations
  server: {
    fs: {
      // Allow serving files from project root
      strict: false,
    },
  },

  optimizeDeps: {
    // Pre-bundle heavy dependencies
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@mui/material',
      '@mui/icons-material',
      '@emotion/react',
      '@emotion/styled',
      '@tanstack/react-query',
      'axios',
    ],
    // Exclude heavy PDF libraries from optimization (lazy-load on demand)
    exclude: ['html2canvas', 'jspdf', 'html2pdf.js'],
    // Force dependency optimization
    force: true,
  },

  build: {
    // Improve build performance
    target: 'esnext',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'mui-vendor': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          'query-vendor': ['@tanstack/react-query'],
        },
      },
    },
  },
})
