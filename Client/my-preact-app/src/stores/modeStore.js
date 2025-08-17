// src/stores/modeStore.js

import { create } from 'zustand';

// Modos permitidos en la interfaz
const MODES = ['classic', 'ai'];

// Leer y validar el modo inicial desde localStorage
const getInitialMode = () => {
  if (typeof window === 'undefined') return 'classic';
  const stored = localStorage.getItem('mode');
  if (MODES.includes(stored)) return stored;
  // Si no existe o está corrupto, volver a 'classic'
  localStorage.setItem('mode', 'classic');
  return 'classic';
};

const useModeStore = create((set) => ({
  mode: getInitialMode(),
  setMode: (newMode) => {
    if (MODES.includes(newMode)) {
      localStorage.setItem('mode', newMode);
      set({ mode: newMode });
    }
  },
}));

export default useModeStore;
