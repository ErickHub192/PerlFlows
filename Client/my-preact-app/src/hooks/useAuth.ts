// src/hooks/useAuth.ts

import useAuthStore from '../stores/authStore';

/**
 * Hook para acceder a autenticación global.
 * - token: valor actual del JWT
 * - login: función para guardar token
 * - logout: función para limpiar token
 * - subscribeToLogout: notifica cuando token cambie a null
 */
export function useAuth() {
  const token = useAuthStore((state) => state.token);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);

  /**
   * Suscribe un callback que se invoca al hacer logout (token === null).
   * @param cb Callback a ejecutar al hacer logout
   * @returns Función para desuscribir
   */
  const subscribeToLogout = (cb: () => void): (() => void) => {
    const unsubscribe = useAuthStore.subscribe((state) => {
      if (state.token === null) {
        cb();
      }
    });
    return unsubscribe;
  };

  return { token, login, logout, subscribeToLogout };
}

/**
 * Devuelve el token directamente desde localStorage (para fetcher).
 */
export function getToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Logout sin depender de hook: limpia store y localStorage.
 */
export function logoutLocal(): void {
  useAuthStore.getState().logout();
}



