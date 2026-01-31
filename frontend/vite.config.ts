import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Base URL - use VITE_BASE_URL env var for flexibility
  // GitHub Pages: /whenwx/ (default)
  // Custom domain: / (set VITE_BASE_URL=/)
  base: process.env.VITE_BASE_URL || '/whenwx/',
  build: {
    sourcemap: true,
  },
  server: {
    port: 3000,
  },
});
