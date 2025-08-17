// Nueva implementación limpia de ChatView basada en mejores prácticas 2025
import { useState, useEffect, useRef } from 'preact/hooks';
import { route } from 'preact-router';
import useChatStore from '../stores/chatStore';
import { useAuth, getToken } from '../hooks/useAuth';
import MessageBubble from '../components/MessageBubble';
import MessageInput from '../components/MessageInput';
import CredentialsManager from '../components/CredentialsManager';
import OAuthRequirementHandler from '../components/OAuthRequirementHandler';
import ModeToggle from '../components/ModeToggle';
import ModelSelector from '../components/ModelSelector';
import DynamicForm from '../components/DynamicForm';
import useModeStore from '../stores/modeStore';

export default function ChatView({ chatId }) {
  const { token } = useAuth();
  const { mode } = useModeStore();
  const [isInitializing, setIsInitializing] = useState(true);
  const [showCredModal, setShowCredModal] = useState(false);
  const [showOAuthRequirements, setShowOAuthRequirements] = useState(false);
  const [oauthRequirements, setOauthRequirements] = useState([]);
  const [showDynamicForm, setShowDynamicForm] = useState(false);
  const [formSchemaEndpoint, setFormSchemaEndpoint] = useState('');
  const [inputValue, setInputValue] = useState('');
  // 🚀 DIRECT APPROACH: Store last response for workflow buttons
  const [lastResponse, setLastResponse] = useState(null);
  // 🔄 TOGGLE STATE: Track workflow activation state
  const [isWorkflowActive, setIsWorkflowActive] = useState(false);
  // 🔧 FLOW ID: Track current flow ID for direct API calls like WorkflowCard
  const [currentFlowId, setCurrentFlowId] = useState(null);
  // 🔄 SAVE STATE: Track save button loading
  const [isSaving, setIsSaving] = useState(false);
  const messagesEndRef = useRef(null);

  
  const {
    activeChatId,
    messages,
    isLoading,
    error,
    setActiveChatId,
    createChat,
    sendMessage,
    loadMessages,
    clearError,
    executeWorkflowDirect,
    saveWorkflowDirect,
    activateWorkflowDirect,
    clearMessagesForNewChat
  } = useChatStore();

  // 🔧 REMOVED: useWorkflows hook - using direct API calls instead

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };


  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 🔄 RECOVERY: Auto-recover workflow state from cache OR messages
  useEffect(() => {
    console.log('🔄 RECOVERY: useEffect ejecutado!', {
      activeChatId,
      hasLastResponse: !!lastResponse,
      messagesCount: messages?.length || 0
    });
    
    // 🚨 CRITICAL FIX: Fresh chat isolation - prevent cache contamination
    const currentMessages = messages[activeChatId];
    const isFreshChat = activeChatId && (!currentMessages || currentMessages.length === 0);
    
    if (isFreshChat && lastResponse) {
      console.log('🧹 FRESH CHAT: Clearing contaminated cache for new chat:', activeChatId, {
        hasMessages: !!currentMessages,
        messageCount: currentMessages?.length || 0,
        hasLastResponse: !!lastResponse
      });
      
      // Clear localStorage cache too to prevent re-contamination
      if (activeChatId) {
        localStorage.removeItem(`workflow_${activeChatId}`);
        console.log('🧹 FRESH CHAT: Removed localStorage cache for:', activeChatId);
      }
      
      setLastResponse(null);
      setCurrentFlowId(null);
      setIsWorkflowActive(false);
      return; // Exit early - fresh chat should have no workflow data
    }
    
    if (activeChatId && !lastResponse) {
      // Estrategia 1: Cache moderno (workflows nuevos)
      try {
        const cached = localStorage.getItem(`workflow_${activeChatId}`);
        if (cached) {
          const workflowCache = JSON.parse(cached);
          console.log('🔄 RECOVERY: Found cached workflow for chat:', activeChatId, '- steps:', workflowCache.execution_plan?.length || 0);
          
          setLastResponse({
            execution_plan: workflowCache.execution_plan || [],
            workflow_created: true,
            metadata: workflowCache.metadata || {}
          });
          
          console.log('🔄 RECOVERY: Workflow buttons habilitados desde cache');
          
          // 🔄 FETCH REAL STATE: Get actual workflow state from backend
          fetch(`/api/chat/${activeChatId}/workflow-status`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
          })
          .then(response => response.ok ? response.json() : null)
          .then(realStatus => {
            if (realStatus) {
              console.log('🔄 INITIAL SYNC: Real workflow state from backend:', realStatus);
              setIsWorkflowActive(realStatus.is_active);
            }
          })
          .catch(error => console.error('🔄 INITIAL SYNC: Error fetching real state:', error));
          return; // Salir aquí si encontramos cache
        }
      } catch (error) {
        console.error('🔄 RECOVERY: Error loading workflow cache:', error);
      }

      // Estrategia 2: Fallback para workflows pre-existentes
      if (messages && messages.length > 0) {
        console.log('🔄 FALLBACK: Buscando execution_plan en mensajes existentes...', messages.length, 'mensajes');
        
        // DEBUG: Ver qué hay en los mensajes
        messages.forEach((msg, i) => {
          if (msg.role === 'assistant' && msg.metadata) {
            console.log(`🔍 DEBUG: Mensaje ${i}:`, {
              role: msg.role,
              has_metadata: !!msg.metadata,
              has_execution_plan: !!msg.metadata.execution_plan,
              execution_plan_length: msg.metadata.execution_plan?.length || 0,
              metadata_keys: Object.keys(msg.metadata)
            });
          }
        });
        
        // Buscar el último mensaje de assistant que tenga execution_plan
        for (let i = messages.length - 1; i >= 0; i--) {
          const message = messages[i];
          if (message.role === 'assistant' && message.metadata?.execution_plan && message.metadata.execution_plan.length > 0) {
            console.log('🔄 FALLBACK: Encontrado execution_plan en mensaje:', message.metadata.execution_plan.length, 'pasos');
            
            setLastResponse({
              execution_plan: message.metadata.execution_plan,
              workflow_created: true,
              metadata: message.metadata || {}
            });
            
            // Cache para futuras visitas
            try {
              const workflowCache = {
                execution_plan: message.metadata.execution_plan,
                workflow_created: true,
                timestamp: Date.now(),
                metadata: message.metadata
              };
              localStorage.setItem(`workflow_${activeChatId}`, JSON.stringify(workflowCache));
              console.log('🔄 FALLBACK: Cached execution_plan from message for future use');
            } catch (error) {
              console.error('🔄 FALLBACK: Error caching from message:', error);
            }
            
            console.log('🔄 FALLBACK: Workflow buttons habilitados desde mensajes');
            break;
          }
        }
      }
    }
  }, [activeChatId, lastResponse, messages]);

  // 🔄 ADDITIONAL: Trigger recovery when messages are loaded
  useEffect(() => {
    if (activeChatId && !lastResponse && messages && messages.length > 0) {
      console.log('🔄 MESSAGES LOADED: Triggering recovery after messages loaded', messages.length);
      
      // Re-run the fallback strategy now that messages are available
      console.log('🔄 FALLBACK: Buscando execution_plan en mensajes existentes...', messages.length, 'mensajes');
      
      // DEBUG: Ver qué hay en los mensajes
      messages.forEach((msg, i) => {
        if (msg.role === 'assistant' && msg.metadata) {
          console.log(`🔍 DEBUG: Mensaje ${i}:`, {
            role: msg.role,
            has_metadata: !!msg.metadata,
            has_execution_plan: !!msg.metadata.execution_plan,
            execution_plan_length: msg.metadata.execution_plan?.length || 0,
            metadata_keys: Object.keys(msg.metadata)
          });
        }
      });
      
      // Buscar el último mensaje de assistant que tenga execution_plan
      for (let i = messages.length - 1; i >= 0; i--) {
        const message = messages[i];
        if (message.role === 'assistant' && message.metadata?.execution_plan && message.metadata.execution_plan.length > 0) {
          console.log('🔄 FALLBACK: Encontrado execution_plan en mensaje:', message.metadata.execution_plan.length, 'pasos');
          
          setLastResponse({
            execution_plan: message.metadata.execution_plan,
            workflow_created: true,
            metadata: message.metadata || {}
          });
          
          // Cache para futuras visitas
          try {
            const workflowCache = {
              execution_plan: message.metadata.execution_plan,
              workflow_created: true,
              timestamp: Date.now(),
              metadata: message.metadata
            };
            localStorage.setItem(`workflow_${activeChatId}`, JSON.stringify(workflowCache));
            console.log('🔄 FALLBACK: Cached execution_plan from message for future use');
          } catch (error) {
            console.error('🔄 FALLBACK: Error caching from message:', error);
          }
          
          console.log('🔄 FALLBACK: Workflow buttons habilitados desde mensajes');
          break;
        }
      }
    }
  }, [messages, activeChatId, lastResponse]);

  // 🔧 FLOW ID LOADER: Use same API as WorkflowCard for reliable data
  useEffect(() => {
    const loadFlowId = async () => {
      if (!activeChatId || !token) return;
      
      try {
        console.log('🔍 LOADING WORKFLOWS like WorkflowCard for chat:', activeChatId);
        
        // 🎯 SAME API AS WORKFLOWCARD: Use /api/flows for reliable data
        const response = await fetch('/api/flows', {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (response.ok) {
          const workflows = await response.json();
          console.log('🔍 ALL WORKFLOWS:', workflows);
          
          // Find workflow that matches this chat_id
          const matchingWorkflow = workflows.find(w => w.chat_id === activeChatId);
          if (matchingWorkflow) {
            console.log('🔍 FOUND MATCHING WORKFLOW:', matchingWorkflow);
            setCurrentFlowId(matchingWorkflow.flow_id);
            setIsWorkflowActive(matchingWorkflow.is_active);
          } else {
            console.log('🔍 NO MATCHING WORKFLOW for chat_id:', activeChatId);
            setCurrentFlowId(null);
            setIsWorkflowActive(false);
          }
        } else {
          console.log('🔍 WORKFLOWS API ERROR:', response.status);
          setCurrentFlowId(null);
          setIsWorkflowActive(false);
        }
      } catch (error) {
        console.error('🔍 WORKFLOWS LOAD ERROR:', error);
        setCurrentFlowId(null);
        setIsWorkflowActive(false);
      }
    };

    loadFlowId();
  }, [activeChatId, token]);

  // 🔄 REMOVED: Complex sync logic


  // 🎯 SmartForm Event Listener - basado en backup legacy
  useEffect(() => {
    const handleSmartFormReady = (event) => {
      const { chatId: eventChatId, smartForm, backendData } = event.detail;
      
      // Solo procesar si es para nuestro chat actual
      if (eventChatId === activeChatId) {
        console.log('🔍 CHATVIEW: Smart form ready event received:', smartForm);
        
        // Set up smart form display
        setFormSchemaEndpoint(null); // Signal this is a smart form
        setShowDynamicForm(true);
      }
    };

    window.addEventListener('smartFormReady', handleSmartFormReady);
    
    return () => {
      window.removeEventListener('smartFormReady', handleSmartFormReady);
    };
  }, [activeChatId]);

  // 🔐 OAuth Requirements Event Listener - Trigger CredentialsManager when OAuth is needed
  useEffect(() => {
    const handleOAuthRequirementsDetected = (event) => {
      const { chatId: eventChatId, oauthRequirements, backendData } = event.detail;
      
      // Solo procesar si es para nuestro chat actual
      if (eventChatId === activeChatId) {
        console.log('🔐 CHATVIEW: OAuth requirements detected event received:', {
          count: oauthRequirements?.length || 0,
          requirements: oauthRequirements
        });
        
        // Open OAuth requirements handler for OAuth flow
        setOauthRequirements(oauthRequirements);
        setShowOAuthRequirements(true);
      }
    };

    window.addEventListener('oauthRequirementsDetected', handleOAuthRequirementsDetected);
    
    return () => {
      window.removeEventListener('oauthRequirementsDetected', handleOAuthRequirementsDetected);
    };
  }, [activeChatId]);

  // Initialize chat with temporal chat support
  useEffect(() => {
    const initializeChat = async () => {
      if (!token) {
        route('/');
        return;
      }

      setIsInitializing(true);
      clearError();

      try {
        if (chatId) {
          // Chat existente - cargar mensajes
          setActiveChatId(chatId);
          await loadMessages(chatId);
          
        } else {
          // 🧹 CLEAR: Clean messages when navigating to /chat/ without ID
          console.log('🆕 Iniciando chat temporal en /chat/ - limpiando estado anterior');
          clearMessagesForNewChat();
          // No setear activeChatId hasta que se cree la sesión real
        }
      } catch (error) {
        console.error('Error initializing chat:', error);
      } finally {
        setIsInitializing(false);
      }
    };

    initializeChat();
  }, [chatId, token]);

  // Handle sending messages with temporal chat support
  const handleSendMessage = async (content) => {
    if (!content.trim()) return;
    
    // 🔧 BEST PRACTICE: Prevent duplicate sends while loading
    if (isLoading) {
      console.log('🚫 Message send blocked - already sending');
      return;
    }
    
    // Clear input after sending
    setInputValue('');

    // 🔧 FIX: Use activeChatId as source of truth, not URL chatId
    // Only create new session if we truly don't have an active chat
    const currentChatId = activeChatId || chatId;
    
    if (!currentChatId) {
      console.log('🆕 Chat temporal en /chat/ detectado, creando sesión real...');
      
      try {
        const newChat = await createChat();
        if (newChat) {
          // 🔧 BEST PRACTICE 2025: Update URL without remounting component
          // Use history.replaceState to avoid component remount and state loss
          const newUrl = `/chat/${newChat.session_id}`;
          window.history.replaceState(null, '', newUrl);
          
          console.log('✅ URL updated silently to:', newUrl);
          
          // Set the new chatId in our local state instead of navigating
          setActiveChatId(newChat.session_id);
          
          // Now send the message directly without navigation delay
          const result = await sendMessage(newChat.session_id, 'user', content.trim());
          
          if (!result) {
            console.error('Failed to send first message');
            setError('Error enviando primer mensaje');
          } else {
            // 🚀 DIRECT APPROACH: Store response for workflow buttons
            setLastResponse(result);
          }
          
          return;
        }
      } catch (error) {
        console.error('Error creando chat:', error);
        setError('Error creando nueva sesión de chat');
        return;
      }
    }

    // Chat existente - enviar mensaje normalmente
    console.log('📤 Sending message to existing chat:', currentChatId);
    const result = await sendMessage(currentChatId, 'user', content.trim());
    
    if (!result) {
      console.error('Failed to send message');
    } else {
      // 🚀 DIRECT APPROACH: Store response for workflow buttons
      setLastResponse(result);
    }
  };

  // 🔐 OAuth Requirements Completion Handler
  const handleOAuthCompleted = async (completedProviders, authData) => {
    console.log('🔐 CHATVIEW: OAuth completed for providers:', completedProviders);
    setShowOAuthRequirements(false);
    setOauthRequirements([]);
    
    // Send a message to continue the workflow with OAuth completed
    const continueMessage = 'OAuth authentication completed successfully. Please continue with the workflow.';
    const result = await sendMessage(activeChatId, 'user', continueMessage);
    
    if (result) {
      setLastResponse(result);
    }
  };

  const handleOAuthError = (error, requirement) => {
    console.error('🔐 CHATVIEW: OAuth error:', error, requirement);
    setShowOAuthRequirements(false);
    setOauthRequirements([]);
    // Could show error message to user here
  };

  // 🎯 SmartForm Submit Handler - basado en backup legacy  
  const handleFormSubmit = async (formData) => {
    setShowDynamicForm(false);

    // ✨ Handle Smart Forms submission (direct to QYRAL AI)
    if (formSchemaEndpoint === null && window.smartFormContext?.isSmartForm) {
      try {
        console.log('[ChatView] Submitting Smart Form with data:', formData);
        console.log('[ChatView] Smart Form context:', window.smartFormContext);

        // Create a user message with the form data for QYRAL AI to process
        const smartFormMessage = `Completé la información requerida: ${JSON.stringify(formData)}`;
        
        // Send the message through normal chat flow
        const result = await sendMessage(activeChatId, 'user', smartFormMessage);
        
        // 🚀 DIRECT APPROACH: Store response for workflow buttons
        if (result) {
          setLastResponse(result);
        }

        // Clear Smart Form context
        window.smartFormContext = null;
        
      } catch (error) {
        console.error('[ChatView] Error submitting Smart Form:', error);
        setError('Error enviando formulario');
      } finally {
        // Always clear context and form state
        window.smartFormContext = null;
      }
    }
  };

  // 🔧 REMOVED: pendingFirstMessage workaround no longer needed
  // The new history.replaceState approach in handleSendMessage eliminates
  // component remounting, so we don't need this temporal message handling

  if (!token) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold mb-4">Acceso Requerido</h2>
          <p className="text-text-secondary mb-4">Debes iniciar sesión para usar el chat</p>
          <button
            onClick={() => route('/')}
            className="btn-primary px-6 py-2 rounded-lg"
          >
            Ir al inicio
          </button>
        </div>
      </div>
    );
  }

  if (isInitializing) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-text-secondary">Inicializando chat...</p>
        </div>
      </div>
    );
  }

  const currentMessages = activeChatId && Array.isArray(messages[activeChatId]) ? messages[activeChatId] : [];


  // 🚀 DIRECT APPROACH: Check if workflow data exists using lastResponse
  const hasWorkflowData = () => {
    // 🚨 CRITICAL FIX: Fresh chat isolation in hasWorkflowData too
    const currentMessages = messages[activeChatId];
    const isFreshChat = activeChatId && (!currentMessages || currentMessages.length === 0);
    
    if (isFreshChat && lastResponse) {
      console.log('🔍 hasWorkflowData: Fresh chat detected with contaminated cache - returning false');
      return false; // Fresh chat should never have workflow data
    }
    
    const hasData = lastResponse && lastResponse.execution_plan && lastResponse.execution_plan.length > 0;
    console.log('🔍 hasWorkflowData check:', {
      hasLastResponse: !!lastResponse,
      hasExecutionPlan: !!lastResponse?.execution_plan,
      planLength: lastResponse?.execution_plan?.length || 0,
      result: hasData
    });
    return hasData;
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-main">
      {/* Header - Glassmorphism style like legacy */}
      <div className="glass border-b border-primary p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <button 
                onClick={() => route('/workflows')}
                className="text-lg font-bold text-text-primary hover:text-purple-400 transition-colors duration-200 cursor-pointer"
              >
                Asistente QYRAL
              </button>
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <div className="status-dot status-active"></div>
                Disponible
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Mode Toggle */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-text-secondary">Modo:</span>
              <ModeToggle />
            </div>
            
            {/* Model Selector - Only show in AI mode */}
            {mode === 'ai' && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-text-secondary">Modelo:</span>
                <div className="min-w-[160px]">
                  <ModelSelector compact={true} />
                </div>
              </div>
            )}
            
            <button className="btn-glass px-2 py-1.5 rounded-lg text-xs font-medium">
              Simular
            </button>
            <button className="btn-glass px-2 py-1.5 rounded-lg text-xs font-medium">
              Métricas
            </button>
            <button 
              onClick={() => setShowCredModal(true)}
              className="btn-primary px-2 py-1.5 rounded-lg text-xs font-medium"
            >
              🔐 Creds
            </button>
            
            {/* Workflow Management Buttons */}
            <button 
              onClick={async () => {
                if (!hasWorkflowData()) {
                  alert('Primero crea un workflow para poder guardarlo');
                  return;
                }
                try {
                  setIsSaving(true);
                  console.log('🔧 FIXED: Saving workflow with execution_plan:', lastResponse.execution_plan.length, 'steps');
                  
                  // 🔧 FIX: Use direct API call with correct format
                  const response = await fetch('/api/chat/workflow-decision', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${getToken()}`
                    },
                    body: JSON.stringify({
                      decision: 'save',
                      chat_id: activeChatId,
                      execution_plan: lastResponse.execution_plan  // 🔧 FIX: Direct execution_plan
                    })
                  });
                  
                  if (!response.ok) {
                    throw new Error(`Error ${response.status}: ${await response.text()}`);
                  }
                  
                  const result = await response.json();
                  console.log('✅ Workflow saved via direct API:', result);
                  
                  // 🔧 UPDATE FLOW_ID: Set the flow_id for future activate operations
                  const flowId = result.workflow_id || result.metadata?.flow_id || result.flow_id || result.id;
                  console.log('🔧 FLOW_ID SEARCH:', {
                    workflow_id: result.workflow_id,
                    'metadata.flow_id': result.metadata?.flow_id,
                    flow_id: result.flow_id,
                    id: result.id,
                    found: flowId
                  });
                  
                  if (flowId) {
                    setCurrentFlowId(flowId);
                    console.log('🔧 FLOW_ID SET after save:', flowId);
                    
                    // 🔧 CACHE: Update localStorage cache with flow_id
                    try {
                      const cached = localStorage.getItem(`workflow_${activeChatId}`);
                      if (cached) {
                        const cache = JSON.parse(cached);
                        cache.flow_id = flowId;
                        localStorage.setItem(`workflow_${activeChatId}`, JSON.stringify(cache));
                        console.log('🔧 CACHE: Updated cache with flow_id');
                      }
                    } catch (e) {
                      console.error('🔧 CACHE: Error updating cache:', e);
                    }
                  } else {
                    console.log('🔧 FLOW_ID MISSING: result keys:', Object.keys(result));
                    console.log('🔧 FLOW_ID MISSING: full result:', result);
                  }
                  
                  // 🎉 SUCCESS FEEDBACK: Show user that workflow was saved
                  const message = flowId ? 
                    '✅ Workflow guardado correctamente! Ahora puedes activarlo con el toggle.' :
                    '✅ Workflow guardado correctamente!';
                  alert(message);
                } catch (error) {
                  console.error('🚨 SAVE ERROR DETAILS:', {
                    message: error.message,
                    stack: error.stack,
                    name: error.name,
                    activeChatId,
                    hasExecutionPlan: !!lastResponse?.execution_plan,
                    planLength: lastResponse?.execution_plan?.length || 0
                  });
                  alert(`Error guardando workflow: ${error.message}`);
                } finally {
                  setIsSaving(false);
                }
              }}
              className={`btn-glass px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                !hasWorkflowData() ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/20'
              }`}
              disabled={!hasWorkflowData() || isLoading || isSaving}
              title={!hasWorkflowData() ? 'Crea un workflow primero' : (currentFlowId ? 'Actualizar workflow existente' : 'Guardar workflow nuevo')}
            >
              {isSaving ? '⏳ Guardando...' : '💾 Guardar'}
            </button>

            {/* Switch tipo toggle para activar/desactivar (del backup) */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">Estado:</span>
              <div className="flex items-center gap-1">
                <span className={`text-xs font-medium ${
                  isWorkflowActive ? 'text-green-400' : 'text-red-400'
                }`}>
                  {isWorkflowActive ? '🟢' : '🔴'}
                </span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isWorkflowActive}
                    onChange={async () => {
                      console.log('🔧 TOGGLE CLICKED: currentFlowId =', currentFlowId);
                      if (!currentFlowId) {
                        console.log('🔧 TOGGLE BLOCKED: No currentFlowId available');
                        alert('Primero GUARDA el workflow, luego podrás activarlo/desactivarlo');
                        return;
                      }
                      
                      try {
                        const newState = !isWorkflowActive;
                        console.log('🔧 SIMPLE TOGGLE: Using flow_id:', currentFlowId, 'newState:', newState);
                        
                        // 🚀 OPTIMISTIC UPDATE: Update UI immediately like WorkflowCard
                        setIsWorkflowActive(newState);
                        
                        // 🎯 EXACT COPY: Same API call as WorkflowCard
                        const response = await fetch(`/api/flows/${currentFlowId}/activate`, {
                          method: 'POST',
                          headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${getToken()}`
                          },
                          body: JSON.stringify({ is_active: newState })
                        });

                        if (!response.ok) {
                          // 🔄 REVERT: On error, revert like WorkflowCard
                          setIsWorkflowActive(!newState);
                          throw new Error(`Error ${response.status}: ${await response.text()}`);
                        }

                        const result = await response.json();
                        console.log('✅ SIMPLE TOGGLE SUCCESS:', result);
                        
                        // ✅ CONFIRM: Update with server response like WorkflowCard
                        setIsWorkflowActive(result.is_active);
                        
                        // 📝 SUCCESS MESSAGE: Add feedback message like other buttons
                        const action = result.is_active ? 'activado' : 'desactivado';
                        // Note: No addMessage function available, will rely on console feedback
                        
                      } catch (error) {
                        console.error('🔧 SIMPLE TOGGLE ERROR:', error);
                        // 🔄 REVERT: Ensure we revert on any error
                        setIsWorkflowActive(!newState);
                        alert(`Error ${newState ? 'activando' : 'desactivando'} workflow: ${error.message}`);
                      }
                    }}
                    disabled={!currentFlowId || isLoading}
                    className="sr-only peer"
                  />
                  <div className={`w-8 h-4 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-purple-500 ${
                    !currentFlowId || isLoading ? 'opacity-50 cursor-not-allowed' : ''
                  }`}></div>
                </label>
              </div>
            </div>

            <button 
              onClick={async () => {
                if (!hasWorkflowData()) {
                  alert('Primero crea un workflow para poder ejecutarlo');
                  return;
                }
                try {
                  console.log('🚀 DIRECT: Executing workflow with execution_plan:', lastResponse.execution_plan.length, 'steps');
                  await executeWorkflowDirect(activeChatId, lastResponse.execution_plan);
                } catch (error) {
                  console.error('Error ejecutando workflow:', error);
                  alert('Error ejecutando workflow');
                }
              }}
              className={`btn-glass px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                !hasWorkflowData() ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-500/20'
              }`}
              disabled={!hasWorkflowData() || isLoading}
              title={!hasWorkflowData() ? 'Crea un workflow primero' : 'Ejecutar workflow ahora'}
            >
              ⚡ Ejecutar
            </button>

            {isLoading && (
              <div className="flex items-center gap-2 text-text-secondary">
                <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full"></div>
                <span className="text-sm">Procesando...</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area - Legacy glass style */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2">
              <span className="text-red-400">⚠️</span>
              <span className="text-red-400 font-medium">Error:</span>
              <span className="text-text-primary">{error}</span>
            </div>
            <button
              onClick={clearError}
              className="mt-2 text-sm text-red-400 hover:text-red-300 underline"
            >
              Cerrar
            </button>
          </div>
        )}

        {currentMessages.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center text-center py-6">
            <div className="w-16 h-16 surface-elevated rounded-2xl flex items-center justify-center mb-4 opacity-80">
              <img 
                src="/logo.svg" 
                alt="QYRAL Logo" 
                className="w-12 h-12"
                style={{ filter: 'none' }}
              />
            </div>
            <h3 className="text-xl font-bold gradient-text mb-2">¡Hola! Soy tu asistente de automatización</h3>
            <p className="text-text-secondary max-w-md text-sm leading-relaxed mb-6">
              Describe lo que quieres automatizar y yo te ayudo a configurarlo paso a paso
            </p>
            
            {/* Suggestion Cards - Más compactas */}
            <div className="grid grid-cols-2 gap-3 max-w-lg w-full mb-4">
              <div 
                onClick={() => handleSendMessage('Quiero automatizar el envío de emails cuando reciba nuevos leads')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">📧</div>
                <div className="font-medium text-text-primary text-sm mb-1">Email Automation</div>
                <div className="text-xs text-text-secondary">Emails automáticos para nuevos leads</div>
              </div>
              
              <div 
                onClick={() => handleSendMessage('Ayúdame a conectar Slack con Google Drive para notificaciones')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">🔗</div>
                <div className="font-medium text-text-primary text-sm mb-1">App Integration</div>
                <div className="text-xs text-text-secondary">Conecta Slack con Google Drive</div>
              </div>
              
              <div 
                onClick={() => handleSendMessage('Quiero programar reportes automáticos cada lunes')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">📊</div>
                <div className="font-medium text-text-primary text-sm mb-1">Scheduled Reports</div>
                <div className="text-xs text-text-secondary">Reportes automáticos semanales</div>
              </div>
              
              <div 
                onClick={() => handleSendMessage('Ayúdame a automatizar la gestión de mi calendario')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">📅</div>
                <div className="font-medium text-text-primary text-sm mb-1">Calendar Management</div>
                <div className="text-xs text-text-secondary">Automatiza tu calendario</div>
              </div>
            </div>
            
            {/* Hint para que sepan que pueden escribir */}
            <div className="text-xs text-text-secondary opacity-60">
              O escribe tu propia idea de automatización abajo ↓
            </div>
          </div>
        ) : (
          <>
            {currentMessages.map((message, i) => (
              <div
                key={message.id}
                className={`flex gap-4 items-start animate-fadeInUp ${
                  message.role === 'user' ? 'flex-row-reverse' : ''
                }`}
              >
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
                  message.role === 'user' 
                    ? 'surface-elevated text-white' 
                    : 'glass text-accent'
                }`}>
                  {message.role === 'user' ? 'TÚ' : 'AI'}
                </div>
                <div className={`max-w-[70%] ${
                  message.role === 'user' ? 'glass surface-elevated border-accent' : 'glass-light'
                } p-4 rounded-2xl transition-all duration-300 hover:transform hover:scale-[1.02]`}>
                  <div className="text-text-primary leading-relaxed whitespace-pre-wrap">
                    {message.content}
                  </div>
                  <div className="text-xs text-text-muted mt-2 flex items-center justify-between">
                    <span>
                      {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {message.isTemp && (
                      <span className="ml-2 text-yellow-500">⏳</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
        
        {/* Loading state for message processing */}
        {isLoading && (
          <div className="flex gap-4 items-start animate-fadeInUp">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold flex-shrink-0 glass text-accent">
              AI
            </div>
            <div className="max-w-[70%] glass-light p-4 rounded-2xl transition-all duration-300">
              <div className="text-text-primary leading-relaxed flex items-center gap-3">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-accent"></div>
                {currentMessages.length === 0 ? 'Creando workflow...' : 'Procesando solicitud...'}
              </div>
              <div className="text-xs text-text-muted mt-2">
                {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area - Legacy glass style */}
      <div className="glass border-t border-primary p-4 bg-gradient-to-r from-glass-dark to-glass-medium">
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(inputValue);
                }
              }}
              placeholder={currentMessages.length === 0 
                ? "💡 ¡Empieza aquí! Describe qué quieres automatizar..." 
                : "💬 Continúa la conversación o ajusta tu automatización..."
              }
              rows={1}
              className="w-full glass-light rounded-xl px-4 py-3 pr-12 text-sm resize-none focus-ring bg-transparent text-text-primary placeholder-text-secondary min-h-[48px] max-h-[120px] border-2 border-primary focus:border-accent"
              style={{ scrollbarWidth: 'none' }}
            />
            <button
              onClick={() => handleSendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 btn-primary w-10 h-10 rounded-lg flex items-center justify-center text-lg disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isLoading ? '⏳' : '🚀'}
            </button>
          </div>
        </div>
      </div>

      {/* Credentials Manager Modal */}
      <CredentialsManager
        isOpen={showCredModal}
        onClose={() => setShowCredModal(false)}
        chatId={activeChatId || chatId}
      />

      {/* 🔐 OAuth Requirements Handler */}
      {showOAuthRequirements && (
        <OAuthRequirementHandler
          oauthRequirements={oauthRequirements}
          chatId={activeChatId || chatId}
          onAllCompleted={handleOAuthCompleted}
          onError={handleOAuthError}
        />
      )}

      {/* 🎯 SmartForm Modal - basado en backup legacy */}
      {showDynamicForm && (
        <DynamicForm
          schemaEndpoint={formSchemaEndpoint}
          smartFormSchema={formSchemaEndpoint === null ? window.smartFormContext?.formSchema : null}
          onSubmit={handleFormSubmit}
          onCancel={() => setShowDynamicForm(false)}
        />
      )}
    </div>
  );
}