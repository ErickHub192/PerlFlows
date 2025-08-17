import { useState } from 'preact/hooks';
import { useToggleFlow, useRunNow } from '../hooks/useWorkflows';
import SimulateDialog from './SimulateDialog';

/**
 * Panel lateral para controlar un workflow desde el chat.
 * @param {{
 *   flow: { flow_id: string, name: string, is_active: boolean, last_run?: string, next_run?: string },
 *   onClose: () => void
 * }} props
 */
export default function WorkflowSidePanel({ flow, onClose }) {
  const [showSim, setShowSim] = useState(false);
  const toggleMutation = useToggleFlow();
  const runNowMutation = useRunNow();

  const handleToggle = () => {
    toggleMutation.mutate({ id: flow.flow_id, is_active: !flow.is_active });
  };

  const handleRunNow = () => {
    runNowMutation.mutate(flow.flow_id);
  };

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-white shadow-lg p-4 flex flex-col">
      <button
        onClick={onClose}
        className="self-end text-gray-500 hover:text-gray-700"
      >✕</button>
      <h3 className="text-xl font-semibold mb-4 truncate">{flow.name}</h3>

      {/* Estado y métricas */}
      {flow.next_run && (
        <p className="text-sm text-gray-600 mb-1">
          Próxima ejecución: <strong>{flow.next_run}</strong>
        </p>
      )}
      {flow.last_run && (
        <p className="text-sm text-gray-600 mb-4">
          Última ejecución: <strong>{flow.last_run}</strong>
        </p>
      )}

      {/* Switch Activo */}
      <div className="flex items-center mb-6">
        <label className="mr-2 font-medium">Activo</label>
        <input
          type="checkbox"
          checked={flow.is_active}
          onChange={handleToggle}
          disabled={toggleMutation.isLoading}
          className="w-5 h-5"
        />
      </div>

      {/* Botones de acción */}
      <div className="space-y-2">
        <button
          onClick={() => setShowSim(true)}
          disabled={!flow.is_active}
          className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 rounded disabled:opacity-50"
        >
          Simular Workflow
        </button>
        <button
          onClick={handleRunNow}
          disabled={!flow.is_active || runNowMutation.isLoading}
          className="w-full bg-green-500 hover:bg-green-600 text-white py-2 rounded disabled:opacity-50"
        >
          {runNowMutation.isLoading ? 'Ejecutando...' : 'Ejecutar Ahora'}
        </button>
      </div>

      {/* Modal de simulación */}
      {showSim && (
        <SimulateDialog
          flowId={flow.flow_id}
          onClose={() => setShowSim(false)}
        />
      )}
    </div>
  );
}
