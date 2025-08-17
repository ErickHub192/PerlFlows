import useModeStore from '../stores/modeStore';

/**
 * Selector de modo: "Clásico" o "Agente" - Diseño moderno unificado
 */
export default function ModeToggle() {
  const mode = useModeStore((state) => state.mode);
  const setMode = useModeStore((state) => state.setMode);

  const handleChange = (newMode) => {
    setMode(newMode);
  };

  return (
    <div className="inline-flex bg-gray-100 dark:bg-gray-800 rounded-2xl p-1 relative">
      {/* Background slider */}
      <div 
        className={`absolute top-1 h-8 bg-white dark:bg-gray-700 rounded-xl shadow-sm transition-all duration-300 ease-out ${
          mode === 'classic' ? 'left-1 w-20' : 'left-[84px] w-16'
        }`}
      />
      
      {/* Buttons */}
      <button
        onClick={() => handleChange('classic')}
        className={`relative z-10 px-4 py-2 text-sm font-medium transition-colors duration-300 rounded-xl ${
          mode === 'classic' 
            ? 'text-gray-900 dark:text-white' 
            : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300'
        }`}
      >
        🔧 Clásico
      </button>
      <button
        onClick={() => handleChange('ai')}
        className={`relative z-10 px-4 py-2 text-sm font-medium transition-colors duration-300 rounded-xl ${
          mode === 'ai' 
            ? 'text-gray-900 dark:text-white' 
            : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300'
        }`}
      >
        🤖 Agente
      </button>
    </div>
  );
}
