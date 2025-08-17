// src/pages/ExecutionsList.jsx

import { useState, useEffect } from 'preact/hooks';
import { Link } from 'preact-router/match';
import { fetcher } from '../api/fetcher';

/**
 * ExecutionsList
 * Muestra la lista de ejecuciones de un flujo dado.
 *
 * Props:
 * - flowId: UUID del flujo cuyas ejecuciones queremos listar
 */
export default function ExecutionsList({ flowId }) {
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (!flowId) return;

    setLoading(true);
    setError('');
    fetcher(`/api/executions/flow/${flowId}`, { method: 'GET' })
      .then(data => {
        setExecutions(data);
      })
      .catch(err => {
        console.error('Error fetching executions:', err);
        setError('No se pudo cargar las ejecuciones');
      })
      .finally(() => setLoading(false));
  }, [flowId]);

  if (loading) {
    return <div>Cargando ejecuciones...</div>;
  }

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  if (executions.length === 0) {
    return <div>No hay ejecuciones para este flujo.</div>;
  }

  return (
    <div className="p-4 bg-white rounded shadow">
      <h2 className="text-xl font-semibold mb-4">Historial de Ejecuciones</h2>
      <table className="w-full table-auto border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="border px-2 py-1 text-left">Inició</th>
            <th className="border px-2 py-1 text-left">Finalizó</th>
            <th className="border px-2 py-1 text-left">Estado</th>
            <th className="border px-2 py-1 text-center">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {executions.map(exec => (
            <tr key={exec.execution_id}>
              <td className="border px-2 py-1">
                {new Date(exec.started_at).toLocaleString()}
              </td>
              <td className="border px-2 py-1">
                {exec.ended_at ? new Date(exec.ended_at).toLocaleString() : '—'}
              </td>
              <td className="border px-2 py-1 capitalize">{exec.status}</td>
              <td className="border px-2 py-1 text-center">
                <Link href={`#/executions/${exec.execution_id}`} className="text-blue-500 underline">
                  Ver detalle
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
