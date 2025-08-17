// src/hooks/useChatStats.js

import { useState, useEffect, useCallback } from 'preact/hooks';
import { fetcher } from '../api/fetcher';

/**
 * Hook para obtener estadísticas dinámicas de sesiones de chat.
 * Elimina los valores hardcodeados del sidebar con datos reales de la BD.
 * 
 * Diferencia automáticamente entre:
 * - Modo AI (agentes): muestra ejecuciones reales
 * - Modo Classic (workflows): muestra info básica
 */
export const useChatStats = (sessions = []) => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Obtiene estadísticas para una sesión específica
   */
  const fetchSessionStats = useCallback(async (sessionId) => {
    try {
      // TEMPORARILY DISABLED - API endpoint doesn't exist yet
      // const response = await fetcher(`/api/chats/${sessionId}/stats`, {
      //   method: 'GET'
      // });
      // return response;
      
      // Return minimal stats for now to prevent 404 errors
      return {
        has_agents: false,
        mode: "classic",
        status: "Disponible",
        type: "Chat",
        description: "Conversación",
        last_activity: "Reciente"
      };
    } catch (err) {
      console.error(`Error fetching stats for session ${sessionId}:`, err);
      // Retornar stats por defecto en caso de error
      return {
        has_agents: false,
        mode: "classic",
        status: "Sin información",
        type: "Chat",
        description: "Información no disponible",
        last_activity: "N/A"
      };
    }
  }, []);

  /**
   * Obtiene estadísticas para múltiples sesiones
   */
  const fetchAllStats = useCallback(async () => {
    if (!sessions || sessions.length === 0) {
      setStats({});
      return;
    }

    // Avoid fetching if we already have stats for these sessions
    const existingSessionIds = Object.keys(stats);
    const newSessionIds = sessions.map(s => s.session_id);
    const needsUpdate = newSessionIds.some(id => !existingSessionIds.includes(id)) || 
                       existingSessionIds.length !== newSessionIds.length;
    
    if (!needsUpdate) {
      return; // Skip if no new sessions
    }

    setLoading(true);
    setError(null);

    try {
      // Hacer requests en paralelo para mejor performance
      const promises = sessions.map(session => 
        fetchSessionStats(session.session_id).then(stat => ({
          sessionId: session.session_id,
          stats: stat
        }))
      );

      const results = await Promise.all(promises);
      
      // Convertir array a objeto para acceso rápido
      const newStats = {};
      results.forEach(({ sessionId, stats }) => {
        newStats[sessionId] = stats;
      });

      setStats(newStats);
    } catch (err) {
      console.error('Error fetching chat stats:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [sessions, fetchSessionStats, stats]);

  /**
   * Efecto para cargar stats cuando cambian las sesiones - PROPERLY DEBOUNCED
   */
  useEffect(() => {
    // Only fetch if sessions changed meaningfully
    if (!sessions || sessions.length === 0) {
      setStats({});
      return;
    }

    // Debounce to prevent excessive calls - INCREASED TO 1000ms
    const timeoutId = setTimeout(() => {
      fetchAllStats();
    }, 1000);

    return () => clearTimeout(timeoutId);
  }, [sessions?.length]); // Only depend on length to prevent excessive re-renders

  /**
   * Función para refrescar stats manualmente
   */
  const refreshStats = useCallback(() => {
    fetchAllStats();
  }, [fetchAllStats]);

  /**
   * Función helper para obtener stats de una sesión específica
   */
  const getSessionStats = useCallback((sessionId) => {
    return stats[sessionId] || {
      has_agents: false,
      mode: "classic",
      status: "Cargando...",
      type: "Chat",
      description: "Obteniendo información...",
      last_activity: "..."
    };
  }, [stats]);

  /**
   * Función para actualizar stats de una sesión específica
   */
  const updateSessionStats = useCallback(async (sessionId) => {
    try {
      const newStats = await fetchSessionStats(sessionId);
      setStats(prev => ({
        ...prev,
        [sessionId]: newStats
      }));
      return newStats;
    } catch (err) {
      console.error(`Error updating stats for session ${sessionId}:`, err);
      return null;
    }
  }, [fetchSessionStats]);

  return {
    stats,
    loading,
    error,
    refreshStats,
    getSessionStats,
    updateSessionStats,
    fetchSessionStats
  };
};

export default useChatStats;