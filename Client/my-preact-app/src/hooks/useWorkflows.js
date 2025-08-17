import { useState, useEffect } from 'preact/hooks';
import { getToken } from './useAuth';

const useWorkflows = () => {
    const [workflows, setWorkflows] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchWorkflows = async () => {
        try {
            setLoading(true);
            setError(null);
            
            console.log('🔍 Fetching workflows...');
            const token = getToken();
            console.log('🔍 Token exists:', !!token);
            
            const response = await fetch('/api/flows', {
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                signal: AbortSignal.timeout(10000) // 10 second timeout
            });

            console.log('🔍 Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('🔍 Error response:', errorText);
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('🔍 Workflows data:', data);
            setWorkflows(data);
            return data;
            
        } catch (err) {
            console.error('🔍 Fetch workflows error:', err);
            setError(err.message);
            return [];
        } finally {
            setLoading(false);
        }
    };

    const createWorkflow = async (workflowData) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/flows/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify(workflowData)
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const newWorkflow = await response.json();
            
            // Actualizar lista de workflows
            setWorkflows(prev => [...prev, newWorkflow]);

            return newWorkflow;
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const getWorkflow = async (flowId) => {
        try {
            const response = await fetch(`/api/flows/${flowId}?includeSpec=true`, {
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            return await response.json();
            
        } catch (err) {
            setError(err.message);
            return null;
        }
    };

    const toggleWorkflowActive = async (flowId, isActive) => {
        try {
            setLoading(true);
            setError(null);

            // 🚀 OPTIMISTIC UPDATE: Actualizar UI inmediatamente
            setWorkflows(prev => 
                prev.map(workflow => 
                    workflow.flow_id === flowId 
                        ? { ...workflow, is_active: isActive }
                        : workflow
                )
            );

            const response = await fetch(`/api/flows/${flowId}/activate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify({ is_active: isActive })
            });

            if (!response.ok) {
                // 🔄 REVERT: Si falla, revertir el estado optimista
                setWorkflows(prev => 
                    prev.map(workflow => 
                        workflow.flow_id === flowId 
                            ? { ...workflow, is_active: !isActive }
                            : workflow
                    )
                );
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const result = await response.json();
            console.log('🔧 HOOK: toggleWorkflowActive response:', result);
            
            // ✅ CONFIRM: Confirmar con la respuesta real del servidor
            setWorkflows(prev => {
                const updated = prev.map(workflow => 
                    workflow.flow_id === flowId 
                        ? { ...workflow, is_active: result.is_active }
                        : workflow
                );
                console.log('🔧 HOOK: Confirmed state:', updated.find(w => w.flow_id === flowId));
                return updated;
            });

            return result;
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const runWorkflow = async (flowId, inputs = {}) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`/api/flows/${flowId}/run-now`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            return await response.json();
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const deleteWorkflow = async (flowId) => {
        try {
            // No usar loading global para delete - se maneja a nivel de componente
            setError(null);

            const response = await fetch(`/api/flows/${flowId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            // Remover de la lista local
            setWorkflows(prev => prev.filter(workflow => workflow.flow_id !== flowId));

            return await response.json();
            
        } catch (err) {
            setError(err.message);
            throw err;
        }
    };

    // Helper para validar spec de workflow antes de guardar
    const validateWorkflowSpec = (spec) => {
        const errors = [];
        
        if (!spec || typeof spec !== 'object') {
            errors.push('Especificación de workflow inválida');
        }
        
        if (!spec.steps || !Array.isArray(spec.steps) || spec.steps.length === 0) {
            errors.push('El workflow debe tener al menos un paso');
        }
        
        // Validar que cada step tenga los campos requeridos
        if (spec.steps) {
            spec.steps.forEach((step, index) => {
                if (!step.node_id) {
                    errors.push(`Paso ${index + 1}: falta node_id`);
                }
                if (!step.action_id) {
                    errors.push(`Paso ${index + 1}: falta action_id`);
                }
            });
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    };

    // Helper para generar nombre automático de workflow
    const generateWorkflowName = (userMessage, steps = []) => {
        if (!userMessage) {
            return `Workflow ${new Date().toLocaleString()}`;
        }
        
        // Extraer primeras palabras del mensaje
        const words = userMessage.trim().split(' ').slice(0, 4);
        let name = words.join(' ');
        
        // Añadir información de pasos si está disponible
        if (steps.length > 0) {
            const uniqueNodes = new Set(steps.map(s => s.node_id || s.name)).size;
            name += ` (${uniqueNodes} servicios)`;
        }
        
        // Limitar longitud
        if (name.length > 50) {
            name = name.substring(0, 47) + '...';
        }
        
        return name;
    };

    // 🆕 NEW: Bridge Service Functions - Eliminan lógica duplicada
    const createWorkflowViaBridge = async (workflowData, chatId) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/chat/workflow-decision', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify({
                    decision: 'save',
                    chat_id: chatId,
                    workflow_context: {
                        workflow_data: workflowData
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Failed to save workflow');
            }

            // Refresh workflows list
            await fetchWorkflows();

            return {
                ...result,
                workflow_id: result.workflow_id
            };
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const activateWorkflowViaBridge = async (workflowData, chatId) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/chat/workflow-decision', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify({
                    decision: 'activate',
                    chat_id: chatId,
                    workflow_context: {
                        workflow_data: workflowData
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Failed to activate workflow');
            }

            // Refresh workflows list
            await fetchWorkflows();

            return result;
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const executeWorkflowViaBridge = async (workflowData, chatId) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/chat/workflow-decision', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify({
                    decision: 'execute',
                    chat_id: chatId,
                    workflow_context: {
                        workflow_data: workflowData
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Failed to execute workflow');
            }

            return result;
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Cargar workflows al montar el hook
    useEffect(() => {
        fetchWorkflows();
    }, []);

    return {
        workflows,
        loading,
        error,
        fetchWorkflows,
        // Legacy functions (mantener para backward compatibility)
        createWorkflow,
        getWorkflow,
        toggleWorkflowActive,
        runWorkflow,
        deleteWorkflow,
        // 🆕 NEW: Bridge Service functions
        createWorkflowViaBridge,
        activateWorkflowViaBridge,
        executeWorkflowViaBridge,
        // Helpers
        validateWorkflowSpec,
        generateWorkflowName
    };
};

// Hook específico para dry run
export const useDryRun = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const dryRun = async (flowId, steps, inputs = {}) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/flows/dry-run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify({
                    flow_id: flowId,
                    steps: steps,
                    test_inputs: inputs,
                    user_id: 1 // TODO: Get from auth context
                })
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            return await response.json();
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    return {
        dryRun,
        loading,
        error
    };
};

// Hook específico para ejecutar workflow inmediatamente
export const useRunNow = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const runNow = async (flowId) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`/api/flows/${flowId}/run-now`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            return await response.json();
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    return {
        runNow,
        loading,
        error
    };
};

// Hook específico para activar/desactivar workflow
export const useToggleFlow = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const toggleFlow = async (flowId, isActive) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`/api/flows/${flowId}/activate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify({ is_active: isActive })
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            return await response.json();
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    return {
        toggleFlow,
        loading,
        error
    };
};

export default useWorkflows;