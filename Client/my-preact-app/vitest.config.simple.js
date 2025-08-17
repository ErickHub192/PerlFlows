// Configuración simple de Vitest para MVP
import { defineConfig } from 'vite';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    exclude: [
      'node_modules/',
      'dist/',
      'e2e/',
      'src/**/*.{test,spec}.{ts,tsx}' // Excluir TypeScript hasta que esté configurado
    ]
  }
});