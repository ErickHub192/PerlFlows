import { useState, useEffect } from 'preact/hooks';
import { Link } from 'preact-router/match';
import { getAgentStatistics } from '../api/agents';

/**
 * Card for displaying agent information with basic statistics
 */
export default function AgentCard({ agent, onUpdate }) {
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);

  useEffect(() => {
    loadStats();
  }, [agent.agent_id]);

  const loadStats = async () => {
    try {
      setLoadingStats(true);
      const statistics = await getAgentStatistics(agent.agent_id);
      setStats(statistics);
    } catch (err) {
      console.error('Error loading agent stats:', err);
    } finally {
      setLoadingStats(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Nunca';
    return new Date(dateStr).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {agent.name}
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(agent.status)}`}>
              {agent.status}
            </span>
            <span className="text-xs text-gray-500">
              {agent.model}
            </span>
          </div>
        </div>
      </div>

      {/* Agent Details */}
      <div className="space-y-2 mb-4">
        <div className="text-sm">
          <span className="text-gray-500">Tools:</span>
          <span className="ml-1 text-gray-700">
            {agent.tools?.length || 0} herramientas
          </span>
        </div>
        <div className="text-sm">
          <span className="text-gray-500">Temperature:</span>
          <span className="ml-1 text-gray-700">{agent.temperature}</span>
        </div>
        <div className="text-sm">
          <span className="text-gray-500">Max Iterations:</span>
          <span className="ml-1 text-gray-700">{agent.max_iterations}</span>
        </div>
      </div>

      {/* Statistics */}
      <div className="border-t pt-4 mb-4">
        <div className="text-center">
          <div className="text-sm text-gray-500">Agente configurado</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Link
          href={`#/agents/${agent.agent_id}`}
          className="flex-1 bg-blue-500 hover:bg-blue-600 text-white text-center py-2 px-3 rounded text-sm transition-colors"
        >
          Ver Detalles
        </Link>
        <Link
          href={`#/agents/${agent.agent_id}/runs`}
          className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-center py-2 px-3 rounded text-sm transition-colors"
        >
          Historial
        </Link>
      </div>

      {/* Creation Date */}
      <div className="mt-3 pt-3 border-t">
        <div className="text-xs text-gray-500">
          Creado: {formatDate(agent.created_at)}
        </div>
      </div>
    </div>
  );
}