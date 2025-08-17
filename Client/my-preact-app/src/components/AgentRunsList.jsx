import { useState, useEffect } from 'preact/hooks';
import { listAgentRuns } from '../api/agents';

export default function AgentRunsList({ agentId }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    if (agentId) {
      loadRuns(1, true);
    }
  }, [agentId, statusFilter]);

  const loadRuns = async (pageNum = 1, reset = false) => {
    try {
      setLoading(true);
      if (reset) setError('');
      
      const data = await listAgentRuns(agentId, pageNum, 20, statusFilter || undefined);
      
      if (reset) {
        setRuns(data.runs || []);
      } else {
        setRuns(prev => [...prev, ...(data.runs || [])]);
      }
      
      setHasMore((data.runs || []).length === 20);
      setPage(pageNum);
    } catch (err) {
      console.error('Error loading runs:', err);
      setError('No se pudieron cargar las ejecuciones');
    } finally {
      setLoading(false);
    }
  };

  const loadMore = () => {
    if (!loading && hasMore) {
      loadRuns(page + 1, false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'succeeded': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'queued': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (startDate, endDate) => {
    if (!endDate) return '—';
    const diff = new Date(endDate) - new Date(startDate);
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  if (loading && runs.length === 0) {
    return (
      <div className="flex justify-center items-center min-h-32">
        <div className="text-gray-600">Cargando ejecuciones...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">
            Filtrar por estado:
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1 text-sm"
          >
            <option value="">Todos</option>
            <option value="succeeded">Exitosas</option>
            <option value="failed">Fallidas</option>
            <option value="running">Ejecutando</option>
            <option value="queued">En Cola</option>
          </select>
        </div>
      </div>

      {/* Runs List */}
      <div className="bg-white rounded-lg shadow">
        {error && (
          <div className="p-4 text-red-500 border-b">
            {error}
            <button 
              onClick={() => loadRuns(1, true)}
              className="ml-2 text-blue-500 hover:underline"
            >
              Reintentar
            </button>
          </div>
        )}

        {runs.length === 0 && !loading ? (
          <div className="p-8 text-center text-gray-500">
            No hay ejecuciones para este agente
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Objetivo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Iniciado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duración
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Resultado
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {runs.map((run) => (
                  <tr key={run.run_id} className="hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <div className="text-sm text-gray-900 max-w-xs truncate">
                        {run.goal || 'Sin objetivo específico'}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-500">
                      {formatDate(run.created_at)}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-500">
                      {formatDuration(run.created_at, run.updated_at)}
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-500 max-w-xs">
                      {run.error && (
                        <div className="text-red-600 truncate" title={run.error}>
                          Error: {run.error}
                        </div>
                      )}
                      {run.result && !run.error && (
                        <div className="text-green-600 truncate">
                          ✓ Completado
                        </div>
                      )}
                      {!run.result && !run.error && run.status === 'running' && (
                        <div className="text-blue-600">
                          En progreso...
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Load More */}
        {hasMore && runs.length > 0 && (
          <div className="p-4 border-t text-center">
            <button
              onClick={loadMore}
              disabled={loading}
              className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white px-4 py-2 rounded text-sm"
            >
              {loading ? 'Cargando...' : 'Cargar Más'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}