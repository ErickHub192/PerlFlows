// src/utils/tokenRefresh.js

import useAuthStore from '../stores/authStore.js';
import { route } from 'preact-router';
import useNotificationStore from '../stores/notificationStore.js';

let refreshPromise = null;

/**
 * Intenta refrescar el token usando el refresh token almacenado
 * Returns: Promise<boolean> - true si se pudo refrescar, false si no
 */
export async function refreshAccessToken() {
  // Evitar múltiples llamadas simultáneas
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        console.log('No refresh token available');
        return false;
      }

      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Actualizar tokens en storage
        useAuthStore.getState().login(data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        
        console.log('Token refreshed successfully');
        return true;
      } else {
        console.log('Failed to refresh token:', response.status);
        return false;
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Configura el refresh automático del token
 * Se ejecuta cada 6 días (1 día antes de que expire el token de 7 días)
 */
export function setupTokenAutoRefresh() {
  const refreshInterval = 6 * 24 * 60 * 60 * 1000; // 6 días en milisegundos
  
  const intervalId = setInterval(async () => {
    const token = useAuthStore.getState().token;
    if (token) {
      console.log('Attempting automatic token refresh...');
      const success = await refreshAccessToken();
      if (!success) {
        console.log('Auto-refresh failed, user will need to login again');
        clearInterval(intervalId);
      }
    } else {
      // No hay token, no necesitamos seguir intentando
      clearInterval(intervalId);
    }
  }, refreshInterval);

  // También intentar refrescar al cargar la página si el token está próximo a expirar
  const token = useAuthStore.getState().token;
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expiresAt = payload.exp * 1000; // Convertir a milisegundos
      const now = Date.now();
      const timeUntilExpiry = expiresAt - now;
      
      // Si el token expira en menos de 1 día, intentar refrescarlo
      if (timeUntilExpiry < 24 * 60 * 60 * 1000) {
        console.log('Token expires soon, attempting refresh...');
        refreshAccessToken();
      }
    } catch (error) {
      console.error('Error parsing token for expiry check:', error);
    }
  }

  return intervalId;
}

/**
 * Interceptor para manejar respuestas 401 con refresh automático
 */
export async function handleAuthError(originalRequest) {
  // Intentar refrescar token
  const refreshSuccess = await refreshAccessToken();
  
  if (refreshSuccess) {
    // Reintentar la petición original con el nuevo token
    const newToken = useAuthStore.getState().token;
    originalRequest.headers.Authorization = `Bearer ${newToken}`;
    return fetch(originalRequest.url, originalRequest);
  } else {
    // No se pudo refrescar, hacer logout
    useAuthStore.getState().logout();
    localStorage.removeItem('refresh_token');
    
    useNotificationStore.getState().add({
      type: 'error',
      message: 'Sesión expirada, por favor vuelve a iniciar sesión.',
    });
    
    route('/', true);
    throw new Error('Session expired');
  }
}