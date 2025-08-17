// src/pages/ExecutionDetail.jsx

import { useState, useEffect } from 'preact/hooks';
import { fetcher } from '../api/fetcher';
import { route } from 'preact-router';

/**
 * ExecutionDetail
 * Muestra la metadata y los pasos de una ejecución específica.
 *
 * Props:
 * - executionId: UUID de la ejecución a cargar
 */
export default function ExecutionDetail({ executionId }) {
  const [detail, setDetail] = useState(null);
  const [steps, setSteps]   = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (!executionId) {
      setError('Execution ID missing');
      return;
    }
    setLoading(true);
    setError('');
    fetcher(`/api/executions/${executionId}`, { method: 'GET' })
      .then(data => {
        setDetail(data.execution);
        setSteps(data.steps);
      })
      .catch(err => {
        console.error('Error fetching execution detail:', err);
        setError('No se pudo cargar el detalle de la ejecución');
      })
      .finally(() => setLoading(false));
  }, [executionId]);

  if (loading) return <div>Cargando detalle...</div>;
  if (error) return <div className="text-red-500">{error}</div>;
  if (!detail) return <div>Ejecución no encontrada.</div>;

  return (
    <div className="p-4 bg-white rounded shadow">
      <button
        className="mb-4 text-blue-500 underline"
        onClick={() => route(`/flows/${detail.flow_id}/executions`)}
      >
        ← Volver al historial
      </button>
      <h2 className="text-xl font-semibold mb-2">Ejecución {detail.execution_id}</h2>
      <ul className="mb-4">
        <li><strong>Flujo:</strong> {detail.flow_id}</li>
        <li><strong>Estado:</strong> {detail.status}</li>
        <li><strong>Inició:</strong> {new Date(detail.started_at).toLocaleString()}</li>
        <li><strong>Finalizó:</strong> {detail.ended_at ? new Date(detail.ended_at).toLocaleString() : '—'}</li>
        {detail.cost != null && <li><strong>Costo:</strong> {detail.cost}</li>}
        {detail.error && <li className="text-red-600"><strong>Error:</strong> {detail.error}</li>}
      </ul>

      <h3 className="text-lg font-semibold mb-2">Pasos de ejecución</h3>
      <table className="w-full table-auto border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="border px-2 py-1">Nodo</th>
            <th className="border px-2 py-1">Acción</th>
            <th className="border px-2 py-1">Estado</th>
            <th className="border px-2 py-1">Inició</th>
            <th className="border px-2 py-1">Finalizó</th>
            <th className="border px-2 py-1">Error</th>
          </tr>
        </thead>
        <tbody>
          {steps.map(step => (
            <tr key={step.step_id}>
              <td className="border px-2 py-1">{step.node_id}</td>
              <td className="border px-2 py-1">{step.action_id}</td>
              <td className="border px-2 py-1 capitalize">{step.status}</td>
              <td className="border px-2 py-1">
                {new Date(step.started_at).toLocaleString()}
              </td>
              <td className="border px-2 py-1">
                {step.ended_at ? new Date(step.ended_at).toLocaleString() : '—'}
              </td>
              <td className="border px-2 py-1 text-red-600">{step.error || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
