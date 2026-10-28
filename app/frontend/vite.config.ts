import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // base: './' is required for Electron's file:// protocol in production builds.
  // Assets will use relative paths so they resolve correctly from dist/index.html.
  base: './',
  plugins: [react()],
  server: {
    port: 3000,
    open: false,
    watch: {
      ignored: ['**/release/**', '**/dist/**'],
    },
  },
});
