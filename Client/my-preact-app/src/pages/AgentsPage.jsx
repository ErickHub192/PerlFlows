import { useState, useEffect } from 'preact/hooks';
import { Link } from 'preact-router/match';
import { listAgents } from '../api/agents';
import AgentCard from '../components/AgentCard';

export default function AgentsPage() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await listAgents();
      setAgents(data);
    } catch (err) {
      console.error('Error loading agents:', err);
      setError('No se pudieron cargar los agentes');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-64">
        <div className="text-gray-600">Cargando agentes...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500 mb-4">{error}</div>
        <button 
          onClick={loadAgents}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">AI Agents</h1>
        <div className="text-sm text-gray-600">
          {agents.length} agente{agents.length !== 1 ? 's' : ''} total{agents.length !== 1 ? 'es' : ''}
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-500 mb-4">No hay agentes creados</div>
          <p className="text-sm text-gray-400 mb-6">
            Los agentes son creados automáticamente cuando PerlFlow AI diseña una automatización que los requiere.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map(agent => (
            <AgentCard 
              key={agent.agent_id} 
              agent={agent}
              onUpdate={loadAgents}
            />
          ))}
        </div>
      )}
    </div>
  );
}