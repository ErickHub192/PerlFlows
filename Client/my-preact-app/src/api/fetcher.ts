// src/api/fetcher.ts

import { route } from 'preact-router';            // Para navegación interna sin full-reload
import { getToken, logoutLocal } from '../hooks/useAuth';
import useNotificationStore from '../stores/notificationStore';

export interface FetchOptions extends RequestInit {
  body?: any;
}

// 🚨 CRITICAL FIX: Request deduplication to prevent multiple identical requests
interface PendingRequest {
  promise: Promise<any>;
  timestamp: number;
}

const pendingRequests = new Map<string, PendingRequest>();
const REQUEST_TIMEOUT = 30000; // 30 seconds timeout
const DEDUPE_WINDOW = 1000; // 1 second deduplication window

/**
 * Generate a unique key for request deduplication
 */
function generateRequestKey(url: string, options: FetchOptions): string {
  const method = options.method || 'GET';
  const body = options.body ? JSON.stringify(options.body) : '';
  const headers = JSON.stringify(options.headers || {});
  
  // Create a hash-like key based on request details
  return `${method}:${url}:${body}:${headers}`;
}

/**
 * Clean up expired pending requests
 */
function cleanupExpiredRequests(): void {
  const now = Date.now();
  for (const [key, request] of pendingRequests.entries()) {
    if (now - request.timestamp > REQUEST_TIMEOUT) {
      pendingRequests.delete(key);
      console.log(`🧹 Cleaned up expired request: ${key.substring(0, 50)}...`);
    }
  }
}

export async function fetcher(
  input: string,
  options: FetchOptions = {}
): Promise<any> {
  // Clean up expired requests periodically
  cleanupExpiredRequests();
  
  // Generate request key for deduplication
  const requestKey = generateRequestKey(input, options);
  
  // Check if identical request is already pending
  const existingRequest = pendingRequests.get(requestKey);
  if (existingRequest) {
    console.log(`🔄 Deduplicating request: ${options.method || 'GET'} ${input}`);
    return existingRequest.promise;
  }
  
  // 1. Obtenemos siempre el token más reciente
  const token = getToken();
  
  // Debug logging for auth issues
  if (input.includes('/api/chats')) {
    console.log('🌐 Making request to', input, 'method:', options.method || 'GET', 'with token:', !!token);
    if (options.method === 'DELETE') {
      console.log('🗑️ DELETE request details:', { 
        url: input, 
        hasToken: !!token,
        tokenPreview: token ? `${token.substring(0, 10)}...` : 'none'
      });
    }
  }

  // 2. Construimos los headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // 3. Create and store the promise for deduplication
  const requestPromise = (async () => {
    try {
      console.log(`📤 Making request: ${options.method || 'GET'} ${input}`);
      
      // Ejecutamos la petición
      const response = await fetch(input, {
        ...options,
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });

      return response;
    } finally {
      // Remove from pending requests when done
      pendingRequests.delete(requestKey);
    }
  })();

  // Store the promise for deduplication
  pendingRequests.set(requestKey, {
    promise: requestPromise,
    timestamp: Date.now()
  });

  const response = await requestPromise;

  // 4. Manejo inteligente de errores 401 con refresh automático
  if (response.status === 401) {
    const errorText = await response.text();
    
    // Solo hacer refresh/logout automático si es realmente un token expirado/inválido
    if (errorText.includes('token') || errorText.includes('expire') || errorText.includes('invalid')) {
      try {
        // Intentar refresh automático del token
        const { refreshAccessToken } = await import('../utils/tokenRefresh.js');
        const refreshSuccess = await refreshAccessToken();
        
        if (refreshSuccess) {
          // Reintentar la petición original con el nuevo token
          const newToken = localStorage.getItem('access_token');
          const retryOptions = {
            ...options,
            headers: {
              ...headers,
              Authorization: `Bearer ${newToken}`,
            },
          };
          
          console.log('Token refreshed, retrying request...');
          return fetcher(input, retryOptions);
        } else {
          throw new Error('Refresh failed');
        }
      } catch (refreshError) {
        // Si el refresh falla, hacer logout
        logoutLocal();

        useNotificationStore.getState().add({
          type: 'error',
          message: 'Sesión expirada, por favor vuelve a iniciar sesión.',
        });

        route('/', true);
        throw { detail: [{ msg: 'Sesión expirada' }] };
      }
    } else {
      // Solo lanzar error sin hacer logout automático
      throw { detail: [{ msg: 'Error de autorización temporal' }] };
    }
  }

  // 5. Intentamos parsear JSON (o null si no viene body)
  let responseBody: any = null;
  try {
    responseBody = await response.json();
  } catch {
    responseBody = null;
  }

  // 6. Si la respuesta no es OK, lanzamos el JSON que obtuvimos (o un detalle genérico)
  if (!response.ok) {
    if (responseBody && typeof responseBody === 'object') {
      // Ya es un objeto, por ejemplo: {detail: [...]}
      throw responseBody;
    } else {
      // No vino body, armar un detalle mínimo
      throw { detail: [{ msg: response.statusText }] };
    }
  }

  // 7. Si todo salió bien, devolvemos el JSON parseado
  return responseBody;
}



