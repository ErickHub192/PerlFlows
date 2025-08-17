// src/stores/authStore.js

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Zustand store para manejar autenticación global:
 * - token: JWT en localStorage
 * - login: guarda token
 * - logout: limpia token
 */
const useAuthStore = create(
  persist(
    (set) => ({
      token: typeof window !== 'undefined' ? localStorage.getItem('access_token') : null,

      login: (newToken, refreshToken = null) => {
        localStorage.setItem('access_token', newToken);
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken);
        }
        set({ token: newToken });
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ token: null });
      },
    }),
    { name: 'auth-store' }
  )
);

export default useAuthStore;
