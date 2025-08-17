import { useState, useEffect } from 'preact/hooks';
import useWorkflows from '../hooks/useWorkflows';
import SimulateDialog from './SimulateDialog';

/**
 * Tarjeta individual para un workflow.
 * @param {{ flow: { flow_id: string, name: string, is_active: boolean, chat_title?: string } }} props
 */
export default function WorkflowCard({ flow, onDelete }) {
  const [isToggling, setIsToggling] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // 🚀 OPTIMISTIC STATE: Estado local que se actualiza inmediatamente
  const [localIsActive, setLocalIsActive] = useState(flow.is_active);
  
  const { toggleWorkflowActive, runWorkflow, deleteWorkflow, workflows } = useWorkflows();

  // 🔄 SYNC: Sincronizar estado local con el estado global
  useEffect(() => {
    const globalWorkflow = workflows.find(w => w.flow_id === flow.flow_id);
    if (globalWorkflow) {
      setLocalIsActive(globalWorkflow.is_active);
    }
  }, [workflows, flow.flow_id]);

  const handleToggle = async () => {
    try {
      setIsToggling(true);
      const newState = !localIsActive;
      
      console.log('🔧 TOGGLE: Before toggle - localIsActive:', localIsActive);
      
      // 🚀 INSTANT UPDATE: Actualizar UI inmediatamente
      setLocalIsActive(newState);
      
      const result = await toggleWorkflowActive(flow.flow_id, newState);
      console.log('🔧 TOGGLE: After toggle - result:', result);
      
      // El estado global ya se actualizó en useWorkflows con optimistic update
      // El useEffect se encargará de sincronizar si hay diferencias
      
    } catch (error) {
      console.error('Error toggling workflow:', error);
      // 🔄 REVERT: Si falla, revertir el estado local
      setLocalIsActive(!newState);
      alert(`Error ${localIsActive ? 'desactivando' : 'activando'} workflow: ${error.message}`);
    } finally {
      setIsToggling(false);
    }
  };

  const handleRunNow = async () => {
    try {
      setIsRunning(true);
      const result = await runWorkflow(flow.flow_id);
      console.log('Workflow execution result:', result);
      alert('✅ Workflow ejecutado correctamente!');
    } catch (error) {
      console.error('Error running workflow:', error);
      alert(`❌ Error ejecutando workflow: ${error.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      // Usar la función de delete pasada desde el padre si existe, sino usar la del hook local
      const deleteFunction = onDelete || deleteWorkflow;
      await deleteFunction(flow.flow_id);
      setShowDeleteConfirm(false);
      // No necesitamos setIsDeleting(false) porque el componente se desmonta
    } catch (error) {
      console.error('Error deleting workflow:', error);
      alert(`❌ Error eliminando workflow: ${error.message}`);
      setIsDeleting(false); // Solo en caso de error
    }
  };

  return (
    <div className="glass rounded-2xl p-6 hover:scale-105 transition-all duration-300 border border-purple-500/20">
      {/* Header con título y botón eliminar */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h2 className="text-xl font-bold text-text-primary mb-1 truncate">{flow.name}</h2>
          {flow.chat_title && (
            <p className="text-sm text-text-secondary truncate">📝 {flow.chat_title}</p>
          )}
        </div>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          disabled={isDeleting}
          className={`p-2 rounded-lg transition-colors ml-2 ${
            isDeleting 
              ? 'text-gray-500 cursor-not-allowed' 
              : 'text-red-400 hover:text-red-300 hover:bg-red-500/10'
          }`}
          title={isDeleting ? "Eliminando..." : "Eliminar workflow"}
        >
          {isDeleting ? '🔄' : '🗑️'}
        </button>
      </div>

      {/* Estado activo/inactivo */}
      <div className="flex items-center justify-between mb-6">
        <span className="text-text-secondary font-medium">Estado:</span>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${
            localIsActive ? 'text-green-400' : 'text-red-400'
          }`}>
            {localIsActive ? '🟢 Activo' : '🔴 Inactivo'}
          </span>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={localIsActive}
              onChange={handleToggle}
              disabled={isToggling}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-500"></div>
          </label>
        </div>
      </div>

      {/* Botón ejecutar */}
      <button
        onClick={handleRunNow}
        disabled={isRunning}
        className="w-full btn-primary py-3 rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isRunning ? '⏳ Ejecutando...' : '▶️ Ejecutar Ahora'}
      </button>

      {/* Modal de confirmación de eliminación */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="glass rounded-2xl p-6 max-w-md mx-4">
            <h3 className="text-xl font-bold text-text-primary mb-4">⚠️ Confirmar eliminación</h3>
            <p className="text-text-secondary mb-6">
              ¿Estás seguro de que quieres eliminar este workflow? Esta acción también eliminará el chat asociado y no se puede deshacer.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 btn-glass py-2 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                  isDeleting
                    ? 'bg-gray-500 cursor-not-allowed text-gray-300'
                    : 'bg-red-500 hover:bg-red-600 text-white'
                }`}
              >
                {isDeleting ? '🔄 Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
