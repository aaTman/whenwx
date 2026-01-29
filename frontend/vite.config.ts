import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Base URL for GitHub Pages deployment
  // Change 'whenwx' to your repository name
  base: '/whenwx/',
  build: {
    sourcemap: true,
  },
  server: {
    port: 3000,
  },
});
