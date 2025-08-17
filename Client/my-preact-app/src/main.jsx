import { render } from 'preact'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './app.jsx'

// Initialize frontend logging (must be imported before any other modules that use console)
import './utils/frontendLogger.js'

// Crear QueryClient
const queryClient = new QueryClient()

// Verificar que el elemento app existe
const appElement = document.getElementById('app');
if (!appElement) {
  throw new Error('No se encontró el elemento #app en el DOM');
}

// Renderizar la aplicación con QueryClientProvider
render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>, 
  appElement
);
