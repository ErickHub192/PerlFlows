import { useEffect } from 'preact/hooks';
import { DEFAULT_AGENT_ID } from '../config';
import { useDeployAgent } from '../hooks/useAgents';

export default function DeployAgentModal({ isOpen, onClose }) {
  const deployMutation = useDeployAgent(DEFAULT_AGENT_ID);

  useEffect(() => {
    if (isOpen) {
      deployMutation.reset && deployMutation.reset();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface text-text-primary p-4 rounded shadow-lg w-80 max-w-[90vw]">
        <h2 className="text-xl font-bold mb-4">Deploy agente</h2>
        <div className="space-y-2">
          <button
            onClick={() => deployMutation.mutate('web')}
            disabled={deployMutation.isLoading}
            className="w-full bg-purple hover:bg-purple-hover text-white py-2 rounded disabled:opacity-50"
          >
            {deployMutation.isLoading ? 'Desplegando…' : 'Web'}
          </button>
          <button
            onClick={() => deployMutation.mutate('telegram')}
            disabled={deployMutation.isLoading}
            className="w-full bg-purple hover:bg-purple-hover text-white py-2 rounded disabled:opacity-50"
          >
            {deployMutation.isLoading ? 'Desplegando…' : 'Telegram'}
          </button>
        </div>
        {deployMutation.isError && (
          <p className="text-red-500 mt-2">Error: {deployMutation.error?.detail || 'fallo'}</p>
        )}
        {deployMutation.isSuccess && (
          <p className="text-green-500 mt-2">{deployMutation.data.message}</p>
        )}
        <div className="mt-4 text-right">
          <button onClick={onClose} className="px-4 py-2 bg-purple hover:bg-purple-hover text-white rounded">
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
