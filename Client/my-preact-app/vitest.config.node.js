// Configuración de Vitest sin dependencias externas - solo Node
import { defineConfig } from 'vite';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node', // Usar Node en lugar de jsdom
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    exclude: [
      'node_modules/',
      'dist/',
      'e2e/',
      'src/**/*.{test,spec}.{ts,tsx}'
    ]
  }
});