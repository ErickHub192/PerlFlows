import { useState, useEffect } from 'preact/hooks';
import useWorkflows from '../hooks/useWorkflows';

const SaveWorkflowModal = ({ isOpen, onClose, workflowData, userMessage, chatId }) => {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    
    const { 
        createWorkflow, // Legacy function (mantener para backup)
        createWorkflowViaBridge, // 🆕 NEW: Bridge Service function
        validateWorkflowSpec, 
        generateWorkflowName 
    } = useWorkflows();

    // Auto-generar nombre cuando se abra el modal
    useEffect(() => {
        if (isOpen && workflowData) {
            const autoName = generateWorkflowName(userMessage, workflowData.steps);
            setName(autoName);
            setError(null);
        }
    }, [isOpen, workflowData, userMessage]);

    const handleSave = async () => {
        if (!workflowData) {
            setError('No hay datos de workflow para guardar');
            return;
        }

        try {
            setSaving(true);
            setError(null);

            // Validar la especificación del workflow
            const validation = validateWorkflowSpec(workflowData);
            if (!validation.isValid) {
                setError(`Workflow inválido: ${validation.errors.join(', ')}`);
                return;
            }

            // Preparar datos para enviar
            const saveData = {
                name: name.trim() || generateWorkflowName(userMessage, workflowData.steps),
                description: description.trim() || null,
                spec: {
                    steps: workflowData.steps || [],
                    inputs: workflowData.inputs || {},
                    outputs: workflowData.outputs || {},
                    metadata: {
                        created_from_chat: true,
                        original_message: userMessage,
                        created_at: new Date().toISOString(),
                        version: '1.0'
                    }
                }
            };

            // 🆕 NEW: Usar Bridge Service si chatId está disponible, sino usar legacy
            let result;
            if (chatId && createWorkflowViaBridge) {
                console.log('🌉 Using Bridge Service to save workflow');
                result = await createWorkflowViaBridge(saveData, chatId);
            } else {
                console.log('🔄 Fallback to legacy createWorkflow');
                result = await createWorkflow(saveData);
            }
            
            // Cerrar modal y notificar éxito
            onClose(result);
            
        } catch (err) {
            setError(`Error guardando workflow: ${err.message}`);
        } finally {
            setSaving(false);
        }
    };

    const handleCancel = () => {
        setName('');
        setDescription('');
        setError(null);
        onClose();
    };

    // Información del workflow para mostrar
    const workflowInfo = workflowData ? {
        stepsCount: workflowData.steps?.length || 0,
        services: [...new Set(workflowData.steps?.map(s => s.node_id || s.name) || [])],
        hasInputs: workflowData.inputs && Object.keys(workflowData.inputs).length > 0,
        hasOutputs: workflowData.outputs && Object.keys(workflowData.outputs).length > 0
    } : null;

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden">
                <div className="px-6 py-4 border-b">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold">💾 Guardar Workflow</h2>
                        <button
                            onClick={handleCancel}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            ✕
                        </button>
                    </div>
                    <p className="text-gray-600 text-sm mt-1">
                        Guarda este workflow para reutilizarlo y programarlo
                    </p>
                </div>
                
                <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 120px)' }}>
                    {/* Información del workflow */}
                    {workflowInfo && (
                        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <h3 className="text-sm font-medium text-blue-800 mb-2">Resumen del Workflow</h3>
                            <div className="text-sm text-blue-700 space-y-1">
                                <div>📝 <strong>{workflowInfo.stepsCount}</strong> pasos</div>
                                <div>🔗 <strong>{workflowInfo.services.length}</strong> servicios: {workflowInfo.services.join(', ')}</div>
                                {workflowInfo.hasInputs && <div>📥 Tiene parámetros de entrada</div>}
                                {workflowInfo.hasOutputs && <div>📤 Genera resultados</div>}
                            </div>
                            {userMessage && (
                                <div className="mt-2 text-xs text-blue-600 italic">
                                    "{userMessage.length > 60 ? userMessage.substring(0, 60) + '...' : userMessage}"
                                </div>
                            )}
                        </div>
                    )}

                    {/* Formulario */}
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Nombre del Workflow *
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="Ej: Automatización de reportes"
                                maxLength={100}
                            />
                            <div className="text-xs text-gray-500 mt-1">
                                {name.length}/100 caracteres
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Descripción (opcional)
                            </label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="Describe qué hace este workflow y cuándo usarlo..."
                                rows={3}
                                maxLength={500}
                            />
                            <div className="text-xs text-gray-500 mt-1">
                                {description.length}/500 caracteres
                            </div>
                        </div>

                        {/* Error message */}
                        {error && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                <div className="text-red-800 text-sm">
                                    ❌ {error}
                                </div>
                            </div>
                        )}

                        {/* Información adicional */}
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                            <div className="text-xs text-gray-600 space-y-1">
                                <div>• El workflow se guardará como <strong>inactivo</strong></div>
                                <div>• Podrás activarlo y programarlo desde "Mis Workflows"</div>
                                <div>• Se guardará una copia de la configuración actual</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                {/* Botones */}
                <div className="px-6 py-4 border-t bg-gray-50 flex justify-end space-x-3">
                    <button
                        onClick={handleCancel}
                        className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 transition-colors"
                        disabled={saving}
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || !name.trim()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex items-center"
                    >
                        {saving ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                Guardando...
                            </>
                        ) : (
                            <>
                                💾 Guardar Workflow
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SaveWorkflowModal;