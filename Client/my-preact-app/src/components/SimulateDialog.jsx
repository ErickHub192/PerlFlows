import { useEffect, useState } from 'preact/hooks';
import { useDryRun } from '../hooks/useWorkflows';
import useWorkflows from '../hooks/useWorkflows';

export default function SimulateDialog({ flowId, onClose }) {
  const [spec, setSpec] = useState(null);
  const dryRunMutation = useDryRun();
  const { getWorkflow } = useWorkflows();

  // 1) Obtén la spec al montar
  useEffect(() => {
    let canceled = false;
    getWorkflow(flowId, true) // true para incluir spec
      .then(data => { if (!canceled) setSpec(data?.spec); })
      .catch(err => console.error('Error cargando spec:', err));
    return () => { canceled = true; };
  }, [flowId, getWorkflow]);

  // 2) Inicia la simulación cuando tengas spec
  useEffect(() => {
    if (spec) {
      dryRunMutation.mutate({
        flow_id: flowId,
        steps: spec.steps,
        // no necesitas user_id si tu backend lo extrae del token
        test_inputs: {},
      });
    }
  }, [spec]);

  // 3) Rendering
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface text-text-primary p-4 rounded shadow-lg w-11/12 max-w-lg max-h-[90vh] overflow-auto">
        <h2 className="text-xl font-bold mb-4">Simulación de Workflow</h2>

        {(!spec || dryRunMutation.isLoading) && (
          <p className="text-center">Simulando…</p>
        )}

        {dryRunMutation.isError && (
          <p className="text-red-500">Error simulando: {dryRunMutation.error.message}</p>
        )}

        {dryRunMutation.isSuccess && (
          <ul className="space-y-2">
            {dryRunMutation.data.steps.map((step, idx) => {
              const ok = step.status === 'success';
              return (
                <li key={idx} className="border border-gray-700 p-2 rounded">
                  <div className="flex items-center justify-between">
                    <span>
                      Paso {idx + 1}: {step.node_name}.{step.action_name}
                    </span>
                    <span className="ml-2">
                      {ok ? '✅' : '⚠️'}
                    </span>
                  </div>
                  <details className="mt-1">
                    <summary>Ver output</summary>
                    <pre className="bg-primary p-2 rounded overflow-auto">
                      {JSON.stringify(step.output, null, 2)}
                    </pre>
                  </details>
                </li>
              );
            })}
          </ul>
        )}

        <div className="mt-4 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-purple hover:bg-purple-hover text-white rounded"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
