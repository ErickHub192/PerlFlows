// src/stores/notificationStore.js

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

/**
 * Notification shape:
 * - id: unique identifier
 * - type: one of 'success' | 'error' | 'info' | 'warning'
 * - message: text to display
 */

const useNotificationStore = create((set) => ({
  notifications: [],

  /**
   * Añade una notificación al store.
   * @param {{ type: string, message: string }} param0
   * @returns {string} id de la notificación creada
   */
  add: ({ type, message }) => {
    const id = uuidv4();
    set((state) => ({
      notifications: [...state.notifications, { id, type, message }],
    }));
    return id;
  },

  /**
   * Elimina una notificación por su id.
   * @param {string} id
   */
  remove: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  /**
   * Limpia todas las notificaciones.
   */
  clear: () => set({ notifications: [] }),
}));

export default useNotificationStore;
