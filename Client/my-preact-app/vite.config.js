import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// Configuración simple para evitar problemas
export default defineConfig({
  plugins: [preact()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
});