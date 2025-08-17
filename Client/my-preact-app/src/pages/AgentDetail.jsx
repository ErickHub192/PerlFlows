import { useState, useEffect } from 'preact/hooks';
import { Link } from 'preact-router/match';
import { getAgent, getAgentAnalytics } from '../api/agents';
import AgentRunsList from '../components/AgentRunsList';
import AgentChart from '../components/AgentChart';

export default function AgentDetail({ agentId }) {
  const [agent, setAgent] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (agentId) {
      loadAgentData();
    }
  }, [agentId]);

  const loadAgentData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const [agentData, analyticsData] = await Promise.all([
        getAgent(agentId),
        getAgentAnalytics(agentId, 30, 10)
      ]);
      
      setAgent(agentData);
      setAnalytics(analyticsData);
    } catch (err) {
      console.error('Error loading agent:', err);
      setError('No se pudo cargar la información del agente');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-64">
        <div className="text-gray-600">Cargando agente...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500 mb-4">{error}</div>
        <Link href="#/agents" className="text-blue-500 hover:underline">
          ← Volver a Agentes
        </Link>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="p-6">
        <div className="text-gray-500 mb-4">Agente no encontrado</div>
        <Link href="#/agents" className="text-blue-500 hover:underline">
          ← Volver a Agentes
        </Link>
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('es-ES');
  };

  const tabs = [
    { id: 'overview', label: 'Resumen' },
    { id: 'runs', label: 'Ejecuciones' },
    { id: 'analytics', label: 'Análisis' }
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <Link href="#/agents" className="text-blue-500 hover:underline mb-2 inline-block">
          ← Volver a Agentes
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{agent.name}</h1>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(agent.status)}`}>
                {agent.status}
              </span>
              <span className="text-sm text-gray-500">Modelo: {agent.model}</span>
            </div>
          </div>
          <div className="text-right text-sm text-gray-500">
            <div>Creado: {formatDate(agent.created_at)}</div>
            {agent.updated_at && (
              <div>Actualizado: {formatDate(agent.updated_at)}</div>
            )}
          </div>
        </div>
      </div>

      {/* Statistics Overview */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-blue-600">{analytics.statistics.total_runs}</div>
            <div className="text-sm text-gray-600">Total Ejecuciones</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-green-600">
              {analytics.statistics.success_rate?.toFixed(1) || 0}%
            </div>
            <div className="text-sm text-gray-600">Tasa de Éxito</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-orange-600">
              {analytics.statistics.average_duration_minutes?.toFixed(1) || 0}m
            </div>
            <div className="text-sm text-gray-600">Duración Promedio</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-purple-600">{analytics.statistics.running_runs}</div>
            <div className="text-sm text-gray-600">Ejecutando Ahora</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Agent Configuration */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Configuración</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Prompt Sistema
                  </label>
                  <div className="bg-gray-50 p-3 rounded text-sm text-gray-700 max-h-32 overflow-y-auto">
                    {agent.default_prompt}
                  </div>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tools Disponibles
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {agent.tools?.map((tool, index) => (
                        <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                          {tool}
                        </span>
                      )) || <span className="text-gray-500 text-sm">Sin tools</span>}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Temperature
                      </label>
                      <div className="text-sm text-gray-900">{agent.temperature}</div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Iteraciones
                      </label>
                      <div className="text-sm text-gray-900">{agent.max_iterations}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            {analytics?.recent_runs && analytics.recent_runs.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Actividad Reciente</h3>
                <div className="space-y-3">
                  {analytics.recent_runs.slice(0, 5).map(run => (
                    <div key={run.run_id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                      <div>
                        <div className="font-medium text-sm">{run.goal || 'Sin objetivo específico'}</div>
                        <div className="text-xs text-gray-500">{formatDate(run.created_at)}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          run.status === 'succeeded' ? 'bg-green-100 text-green-800' :
                          run.status === 'failed' ? 'bg-red-100 text-red-800' :
                          run.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {run.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'runs' && (
          <AgentRunsList agentId={agentId} />
        )}

        {activeTab === 'analytics' && analytics && (
          <AgentChart analytics={analytics} />
        )}
      </div>
    </div>
  );
}