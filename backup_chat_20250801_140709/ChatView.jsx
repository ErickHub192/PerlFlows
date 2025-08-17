// src/pages/ChatView.jsx

import { useState, useEffect, useRef, useCallback, useMemo } from 'preact/hooks';
import DynamicForm from '../components/DynamicForm';
import ClarifyModal from '../components/ClarifyModal';
import ModeToggle from '../components/ModeToggle';
import ModelSelector from '../components/ModelSelector';
import { fetcher } from '../api/fetcher';
import WorkflowSidePanel from '../components/WorkflowSidePanel';
import CredentialsManager from '../components/CredentialsManager';
import OAuthRequirementHandler from '../components/OAuthRequirementHandler';
import SaveWorkflowModal from '../components/SaveWorkflowModal';
import DeployAgentModal from '../components/DeployAgentModal';
import useChatStore from '../stores/chatStore';
import useModeStore from '../stores/modeStore';
import useWorkflows from '../hooks/useWorkflows';
import { useAuth } from '../hooks/useAuth';
import { route } from 'preact-router';

export default function ChatView({ chatId }) {
  // — Auth check —
  const { token } = useAuth();
  const isAuthenticated = !!token;
  
  // — Mode store —
  const { mode } = useModeStore();
  
  // — Workflows hook (same as WorkflowCard) —
  const { workflows, toggleWorkflowActive } = useWorkflows();

  // — Zustand store hooks —
  const setActiveChat  = useChatStore(s => s.setActiveChat);
  const addChat        = useChatStore(s => s.addChat);
  const chatHistories  = useChatStore(s => s.chatHistories);
  const fetchMessages  = useChatStore(s => s.fetchMessages);
  const postMessage    = useChatStore(s => s.sendMessage);
  const addAssistantMessage = useChatStore(s => s.addAssistantMessage);
  const cleanSystemMessages = useChatStore(s => s.cleanSystemMessages);
  // 💾 BD-FIRST: Polling functions for real-time reactivity
  const startPolling   = useChatStore(s => s.startPolling);
  const stopPolling    = useChatStore(s => s.stopPolling);
  const stopAllPolling = useChatStore(s => s.stopAllPolling);
  
  // Get chat history safely and filter for UI display
  const rawChatHistory = chatHistories[chatId] || [];
  const chatHistory = useChatStore(s => s.filterSystemMessages)(rawChatHistory);
  
  // ✅ FIX: Debug chat history filtering
  useEffect(() => {
    console.log('📝 CHATVIEW: History update', {
      chatId,
      raw: rawChatHistory.length,
      filtered: chatHistory.length,
      lastMessage: chatHistory[chatHistory.length - 1]
    });
  }, [chatId, rawChatHistory.length, chatHistory.length]);
  
  // Get last response for workflow state management
  const lastResponse = useMemo(() => {
    if (chatHistory.length > 0) {
      const lastMessage = chatHistory[chatHistory.length - 1];
      if (lastMessage?.role === 'assistant' && lastMessage?.data) {
        try {
          const parsed = JSON.parse(lastMessage.data);
          // 🔧 FIX: Handle different response structures
          console.log('🔍 DEBUG lastResponse:', parsed);
          return parsed;
        } catch (e) {
          console.warn('Error parsing message data:', e);
          return null;
        }
      }
    }
    return null;
  }, [chatHistory]);
  
  // State for workflow modifications
  const [isModifyingWorkflow, setIsModifyingWorkflow] = useState(false);
  
  // 🔄 SAME LOGIC AS WORKFLOWCARD: Local optimistic state for workflow activation
  const [localWorkflowActive, setLocalWorkflowActive] = useState(false);
  const [currentWorkflowId, setCurrentWorkflowId] = useState(null);
  
  // 🔄 SAME LOGIC AS WORKFLOWCARD: Find current workflow by chat_id
  const currentWorkflow = workflows.find(w => w.chat_id === chatId);
  
  // 🔄 SAME LOGIC AS WORKFLOWCARD: Sync local state with global state
  useEffect(() => {
    if (currentWorkflow) {
      setLocalWorkflowActive(currentWorkflow.is_active);
      setCurrentWorkflowId(currentWorkflow.flow_id);
    } else {
      setLocalWorkflowActive(false);
      setCurrentWorkflowId(null);
    }
  }, [currentWorkflow]);
  
  // 🚀 OPTIMIZED: Simple and direct button state management
  const buttonStates = useMemo(() => {
    // Handle loading states first
    if (isModifyingWorkflow) {
      return { save: 'guardando...', activate: 'activando...', execute: 'ejecutando...' };
    }
    
    if (!lastResponse) {
      return { save: 'esperando', activate: 'esperando', execute: 'esperando' };
    }
    
    const status = lastResponse.status;
    const workflowAction = lastResponse.workflow_action;
    const hasSteps = lastResponse.steps && lastResponse.steps.length > 0;
    
    console.log('🔧 BUTTON STATE DEBUG:', { status, workflowAction, hasSteps, isModifyingWorkflow });
    
    // State machine for button labels based on backend status values
    let saveLabel = 'esperando';
    let activateLabel = 'esperando';
    let executeLabel = 'esperando';
    
    // 🎯 FIX: Check for workflow ready states from backend
    if (hasSteps || status === 'ready' || status === 'ready_for_review') {
      saveLabel = 'guardar';
      activateLabel = 'esperando';  // Can't activate until saved
      executeLabel = 'ejecutar ahora';  // Can execute immediately
    }
    
    // Backend returns 'save_workflow' when workflow is saved
    if (status === 'save_workflow' || workflowAction === 'save') {
      saveLabel = 'guardado ✓';
      activateLabel = 'activar';
      executeLabel = 'ejecutar ahora';
    }
    
    // Backend returns 'activate_workflow' when workflow is activated
    if (status === 'activate_workflow' || workflowAction === 'activate') {
      saveLabel = 'guardado ✓';
      activateLabel = 'activado ✓';
      executeLabel = 'ejecutar ahora';
    }
    
    // Backend returns 'execute_workflow' when workflow was executed
    if (status === 'execute_workflow' || workflowAction === 'execute') {
      saveLabel = 'guardado ✓';
      activateLabel = 'activado ✓';
      executeLabel = 'ejecutado ✓';
    }
    
    return { save: saveLabel, activate: activateLabel, execute: executeLabel };
  }, [lastResponse, isModifyingWorkflow]);
  
  // 🚀 OPTIMIZED: Simple workflow ready check
  const isWorkflowReady = lastResponse && (
    lastResponse.steps?.length > 0 || 
    lastResponse.status === 'ready' || 
    lastResponse.status === 'ready_for_review' ||
    lastResponse.status === 'save_workflow' ||
    lastResponse.status === 'activate_workflow' ||
    lastResponse.status === 'execute_workflow'
  );
  
  // 🔍 DEBUG Enhanced logging
  console.log('🔍 OPTIMIZED Button State:', {
    buttonStates,
    isWorkflowReady,
    lastResponseStatus: lastResponse?.status,
    lastResponseAction: lastResponse?.workflow_action,
    hasSteps: lastResponse?.steps?.length > 0,
    metadata: lastResponse?.metadata,
    fullLastResponse: lastResponse,
    localWorkflowActive,
    currentWorkflowId,
    currentWorkflow
  });
  
  // 🔧 FIX: Log button enabling conditions
  console.log('🔍 DEBUG Button Conditions:', {
    condition1_hasSteps: (lastResponse?.steps && lastResponse.steps.length > 0),
    condition2_ready: lastResponse?.status === 'ready',
    condition3_readyForReview: lastResponse?.status === 'ready_for_review',
    condition4_saveWorkflow: lastResponse?.status === 'save_workflow',
    condition5_activateWorkflow: lastResponse?.status === 'activate_workflow',
    condition6_executeWorkflow: lastResponse?.status === 'execute_workflow',
    currentStatus: lastResponse?.status,
    finalResult: isWorkflowReady
  });
  
  // Get button state and text based on workflow status
  // ✅ REMOVED: getButtonState function - replaced with optimized buttonStates

  // Determine if this is a new chat (no chatId provided)
  const isNewChat = !chatId;

  // Enhanced validation and redirection
  useEffect(() => {
    // Validate authentication first
    if (!isAuthenticated) {
      console.warn('Not authenticated, redirecting to home');
      route('/', true);
      return;
    }

    // If we have a chatId, validate it's a proper UUID
    if (chatId && (chatId === 'undefined' || chatId.startsWith('fallback-') || chatId === 'new')) {
      console.warn('Invalid chatId detected:', chatId, 'redirecting to new chat');
      route('/chat', true);
      return;
    }
  }, [chatId, isAuthenticated]);

  // Don't render if validation fails
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-text-secondary">Cargando...</div>
      </div>
    );
  }

  // ✅ FIX: Clean system messages on component mount (one-time cleanup)
  useEffect(() => {
    // Only clean if this is the first time mounting the app
    if (!window._systemMessagesCleaned) {
      console.log('🧹 Performing one-time system messages cleanup');
      cleanSystemMessages();
      window._systemMessagesCleaned = true;
    }
  }, []); // Run only once on mount

  // 1️⃣ Marcar chat activo y cargar mensajes - OPTIMIZED + BD-FIRST POLLING
  useEffect(() => {
    let isMounted = true;
    
    // Only load messages if we have a valid chatId (not new chat)
    if (chatId && chatId !== 'undefined') {
      setActiveChat(chatId);
      
      const loadMessages = async () => {
        try {
          if (isMounted) {
            // ✅ FIX: Only fetch if no messages are loaded to avoid duplicate calls
            const currentMessages = chatHistories[chatId];
            if (!currentMessages || currentMessages.length === 0) {
              console.log('🔄 ChatView: Loading messages for chat:', chatId);
              await fetchMessages(chatId);
            } else {
              console.log('📋 ChatView: Messages already loaded for chat:', chatId, '- count:', currentMessages.length);
            }
          }
        } catch (err) {
          console.error('❌ ChatView: Error loading messages:', err);
        }
      };
      
      loadMessages();
      
      // 💾 BD-FIRST: Temporarily disabled aggressive polling during development
      // console.log('💾 BD-FIRST: Starting reactive polling for chat:', chatId);
      // startPolling(chatId);
      
      // Handle pending first message after navigation - FIXED
      if (window.pendingFirstMessage && !window.pendingMessageProcessed) {
        const pendingMsg = window.pendingFirstMessage;
        window.pendingFirstMessage = null; // Clear immediately to prevent duplicates
        window.pendingMessageProcessed = true; // Prevent multiple processing
        
        console.log('📨 Sending pending message via local sendMessage:', pendingMsg);
        
        // Use store directly to avoid isNewChat logic loop
        setTimeout(() => {
          useChatStore.getState().sendMessage(chatId, 'user', pendingMsg)
            .finally(() => {
              window.pendingMessageProcessed = false; // Reset after completion
            });
        }, 100);
      }
    }
    
    return () => {
      isMounted = false;
      // 💾 BD-FIRST: Stop polling when chat changes or component unmounts (disabled during dev)
      // if (chatId && chatId !== 'undefined') {
      //   stopPolling(chatId);
      // }
    };
  }, [chatId]); // Solo depende de chatId para evitar bucles

  // — Local UI state —
  const [message, setMessage]                         = useState('');
  const [selectedNodes, setSelectedNodes]             = useState([]);
  const [simpleQuestions, setSimpleQuestions]         = useState([]);
  const [simpleAnswers, setSimpleAnswers]             = useState({});
  const [pendingNodes, setPendingNodes]               = useState([]);
  const [currentNodeIndex, setCurrentNodeIndex]       = useState(0);
  const [showOAuthButton, setShowOAuthButton]         = useState(false);
  const [oauthService, setOauthService]               = useState('');
  const [oauthSchemaEndpoint, setOauthSchemaEndpoint] = useState('');
  const popupRef = useRef(null);
  const isProcessingRef = useRef(false);
  const lastUserMessageRef = useRef(null);
  const [showDynamicForm, setShowDynamicForm]         = useState(false);
  const [formSchemaEndpoint, setFormSchemaEndpoint]   = useState('');
  const [currentNode, setCurrentNode]                 = useState('');
  const [currentAction, setCurrentAction]             = useState('');
  const [finalizeReady, setFinalizeReady]             = useState(false);
  const [workflow, setWorkflow]                       = useState(null);
  const [flowMeta, setFlowMeta]                       = useState(null);
  const [showCredModal, setShowCredModal]             = useState(false);
  // ✨ NEW: Service suggestions (LLM + CAG dropdown)
  const [serviceSuggestions, setServiceSuggestions]   = useState([]);
  const [showServiceSelection, setShowServiceSelection] = useState(false);
  // ✨ NEW: Save workflow functionality
  const [showSaveWorkflowModal, setShowSaveWorkflowModal] = useState(false);
  const [lastWorkflowData, setLastWorkflowData] = useState(null);
  const [lastUserMessage, setLastUserMessage] = useState('');
  const [isAutoFinalizing, setIsAutoFinalizing] = useState(false); // Bandera de control
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [isCreatingChat, setIsCreatingChat] = useState(false); // Loading state for chat creation
  const [isSendingMessage, setIsSendingMessage] = useState(false); // Loading state for messages



  // 🚨 CRITICAL FIX: Better loading state management based on store
  useEffect(() => {
    if (isSendingMessage && chatHistory.length > 0) {
      const lastMessage = chatHistory[chatHistory.length - 1];
      // Check if we have a successful assistant response (not error/loading)
      if (lastMessage.role === 'assistant' && !lastMessage.error && lastMessage.status !== 'sending') {
        console.log('🎯 LLM response detected, resetting loading state');
        setIsSendingMessage(false);
      }
    }
  }, [chatHistory, isSendingMessage]);

  // 🔧 FIX 1A: REMOVED OAuth already satisfied handler to prevent duplicate messages
  // This was causing duplicate sendMessage() calls alongside the onAllCompleted callback
  // Now only onAllCompleted handles OAuth continuation for consistent behavior

  // ✨ NEW: Listen for smart form events from chatStore
  useEffect(() => {
    const handleSmartFormReady = (event) => {
      const { chatId: eventChatId, smartForm, backendData } = event.detail;
      
      // Only process if it's for the current chat
      if (eventChatId === chatId) {
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
  }, [chatId]);

  // Eliminar mensajes vacíos de “assistant” y simplificar la forma de pasar la conversación
  const sanitizeConversation = (conv) =>
    conv
      .filter(m => !(m.role === 'assistant' && !m.content?.trim()))
      .map(m => ({ role: m.role, content: m.content }));

  // 2️⃣ Función para llamar al endpoint /api/chat
  const callChat = async (userMsg, updatedHistory) => {
    try {
      console.debug('[ChatView] Enviando a /api/chat:', {
        session_id: chatId,
        message: userMsg,
        conversation: sanitizeConversation(updatedHistory),
      });

      // ✅ NUEVA LÓGICA: Manejar chats temporales
      const isTemporaryChat = chatId && chatId.startsWith('temp-');
      
      return await fetcher('/api/chat', {
        method: 'POST',
        body: {
          session_id: isTemporaryChat ? null : chatId, // null para chats temporales
          message: userMsg,
          conversation: sanitizeConversation(updatedHistory),
          workflow_type: useModeStore.getState().mode === 'ai' ? 'agent' : 'classic',
        },
      });
    } catch (err) {
      console.error('[ChatView] Error en callChat:', err);

      // 1) Si es instancia de Error, imprimimos message y stack
      if (err instanceof Error) {
        console.error('[ChatView] err.message:', err.message);
        try {
          const allProps = JSON.stringify(
            err,
            Object.getOwnPropertyNames(err),
            2
          );
          console.error('[ChatView] Detalle interno de Error (propiedades):', allProps);

          if (typeof err.message === 'object') {
            console.error(
              '[ChatView] Detalle de err.message (si es objeto):',
              JSON.stringify(err.message, null, 2)
            );
          }
        } catch (stringifyErr) {
          console.error('[ChatView] No se pudo serializar propiedades de err:', stringifyErr);
        }
      }
      // 2) Si tiene la forma { detail: [ ... ] }, interpretamos como error de API
      else if (
        err &&
        typeof err === 'object' &&
        'detail' in err &&
        Array.isArray(err.detail)
      ) {
        console.error('[ChatView] Error de API:', err.detail);
        // Aquí podrías mostrar un mensaje al usuario, por ejemplo:
        // alert(err.detail[0]?.msg || 'Error desconocido de API');
      }
      // 3) Cualquier otro caso: intentamos serializar
      else {
        try {
          console.error(
            '[ChatView] Error inesperado (no es instancia de Error ni formato API):',
            JSON.stringify(err, null, 2)
          );
        } catch (jsonErr) {
          console.error('[ChatView] No pudo serializar err no-Error:', err);
        }
      }

      return {}; // para no romper la app, devolvemos objeto vacío
    }
  };

  // 3️⃣ Reenviar último mensaje tras autorización OAuth (con deduplicación)
  const resendLastMessage = () => {
    console.log('[ChatView] resendLastMessage called:', {
      hasLastMessage: !!lastUserMessageRef.current,
      isProcessing: isProcessingRef.current,
      lastMessage: lastUserMessageRef.current
    });
    // ✅ MANTENER: OAuth resend logic intacta, solo con mejor control
    if (lastUserMessageRef.current && !isProcessingRef.current && !isSendingMessage) {
      console.log('[ChatView] OAuth resending message:', lastUserMessageRef.current);
      sendMessage(lastUserMessageRef.current);
    }
  };

  // Handle first message in new chat - simple and reliable
  const handleFirstMessage = async (content) => {
    setIsCreatingChat(true);
    try {
      console.log('🚀 Creating chat:', content);
      
      // Create chat
      const newChatId = await addChat();
      console.log('✅ Chat created:', newChatId);
      
      // Set active and navigate
      setActiveChat(newChatId);
      route(`/chat/${newChatId}`, true);
      
      // Store message to send after navigation completes
      window.pendingFirstMessage = content;
      
    } catch (err) {
      console.error('Error creating new chat:', err);
      const errorMsg = err.message || 'Error desconocido';
      alert(`Error creando nuevo chat: ${errorMsg}. Verifica que el backend esté funcionando.`);
    } finally {
      setIsCreatingChat(false);
      // 🔧 FIX: Reset loading state for first message
      setIsSendingMessage(false);
    }
  };

  // 4️⃣ Enviar mensaje de usuario
  const sendMessage = async (overrideMsg) => {
    console.log('🔥 SendMessage function called with:', overrideMsg);
    const userMsg = overrideMsg ?? message;
    
    if (!userMsg.trim()) {
      console.log('🔥 SendMessage returning early - no message');
      return;
    }
    
    // ✅ CRITICAL FIX: Stronger duplicate prevention
    if (isSendingMessage) {
      console.log('🔥 SendMessage blocked - already sending, preventing duplicate');
      return;
    }

    // ✅ FIX: Check for recent identical messages to prevent rapid duplicates
    const recentMessages = chatHistory.slice(-3); // Check last 3 messages
    const hasDuplicateRecent = recentMessages.some(msg => 
      msg.role === 'user' && 
      msg.content === userMsg &&
      (Date.now() - new Date(msg.timestamp).getTime()) < 10000 // 10 seconds
    );

    if (hasDuplicateRecent) {
      console.log('🚫 Preventing duplicate message - identical message sent recently');
      return;
    }
    

    console.log('🚀 SendMessage proceeding with:', userMsg);
    setIsSendingMessage(true);
    lastUserMessageRef.current = userMsg;
    setMessage('');

    // If this is a new chat, create session first
    if (isNewChat) {
      console.log('🆕 New chat detected, creating session...');
      await handleFirstMessage(userMsg);
      return;
    }

    try {
      // ✅ FIX: Single call to store which handles everything
      const response = await useChatStore.getState().sendMessage(chatId, 'user', userMsg);
      console.log('✅ Message sent successfully via store');
      
    } catch (err) {
      console.error('[ChatView] Error en sendMessage:', err);
      addAssistantMessage(chatId, 'Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo.', {
        status: 'error'
      });
    } finally {
      setIsSendingMessage(false);
    }
  };


  // 🔥 NEW: Smart Forms API functions
  const checkSmartFormSupport = async (handlerName) => {
    try {
      const response = await fetch(`/api/smart-forms/should-use-smart/${handlerName}`);
      if (!response.ok) throw new Error('Failed to check smart form support');
      return await response.json();
    } catch (error) {
      console.error('[ChatView] Error checking smart form support:', error);
      return { use_smart_form: false, form_type: 'traditional' };
    }
  };

  const analyzeParameters = async (handlerName, discoveredParams = {}) => {
    try {
      const response = await fetch('/api/smart-forms/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          handler_name: handlerName,
          discovered_params: discoveredParams
        })
      });
      if (!response.ok) throw new Error('Failed to analyze parameters');
      return await response.json();
    } catch (error) {
      console.error('[ChatView] Error analyzing parameters:', error);
      return { missing_params: [], can_execute: false };
    }
  };

  const getMissingParametersForm = async (handlerName, discoveredParams = {}) => {
    try {
      const response = await fetch('/api/smart-forms/get-missing-form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          handler_name: handlerName,
          discovered_params: discoveredParams
        })
      });
      if (!response.ok) throw new Error('Failed to get missing parameters form');
      return await response.json();
    } catch (error) {
      console.error('[ChatView] Error getting missing parameters form:', error);
      return null;
    }
  };

  const executeWithUserInput = async (handlerName, discoveredParams, userParams, creds = {}) => {
    try {
      const response = await fetch('/api/smart-forms/execute-with-user-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          handler_name: handlerName,
          discovered_params: discoveredParams,
          user_provided_params: userParams,
          execution_creds: creds
        })
      });
      if (!response.ok) throw new Error('Failed to execute with user input');
      return await response.json();
    } catch (error) {
      console.error('[ChatView] Error executing with user input:', error);
      throw error;
    }
  };


  // ✨ NEW: Función para manejar selección de servicios
  const handleServiceSelection = async (selectedServices) => {
    console.debug('[ChatView] Services selected:', selectedServices);
    
    // 🔥 NEW: Add visual feedback for service selection
    const serviceNames = Array.isArray(selectedServices) 
      ? selectedServices.map(id => {
          // Find service name from suggestions
          for (const group of serviceSuggestions) {
            const option = group.options?.find(opt => opt.node_id === id);
            if (option) return option.name;
          }
          return id; // fallback to ID
        }).join(', ')
      : 'servicio seleccionado';
    
    // ✅ FIX: Service selection feedback - UI only, no duplication
    console.log('💫 Service selection feedback - UI only, not sending to backend');
    useChatStore.getState().addMessage(chatId, {
      role: 'user',
      content: `✅ ${serviceNames} seleccionado`,
      timestamp: new Date().toISOString(),
      status: 'sent',
      isSelectionFeedback: true, // Mark this as UI feedback, not real user input
      skipBackend: true // Prevent backend sending
    });
    
    // Cerrar modal de selección
    setShowServiceSelection(false);
    setServiceSuggestions([]);
    
    // 🔧 FIX: Limpiar pending service selection para evitar que se reactive
    if (window.pendingServiceSelection) {
      delete window.pendingServiceSelection;
    }

    // Usar el método del store para mantener consistencia
    try {
      const response = await useChatStore.getState().sendMessageWithServices(
        chatId,
        lastUserMessageRef.current, // Reutilizar el último mensaje  
        selectedServices,
        mode === 'ai' ? 'agent' : 'classic'
      );

      // Manejar casos especiales que no están en el store
      if (response.nodes?.length) {
        setSelectedNodes(response.nodes);
        setPendingNodes(response.nodes);
        setCurrentNodeIndex(0);
        return;
      }

      if (response.finalize) {
        setFinalizeReady(true);
      }
    } catch (err) {
      console.error('[ChatView] Error en handleServiceSelection:', err);
      // 🚨 CRITICAL FIX: Use addAssistantMessage to avoid API call
      addAssistantMessage(chatId, 'Lo siento, hubo un error procesando tu selección. Por favor intenta de nuevo.', {
        status: 'error'
      });
    }
  };

  // 5️⃣ Confirmar finalización de workflow
  const confirmFinalize = useCallback(async () => {
    try {
      const data = await fetcher('/api/chat/finalize', {
        method: 'POST',
        body: {
          session_id: chatId,
          message: '',
          conversation: sanitizeConversation(chatHistory),
        },
      });

      setWorkflow({
        executionId: data.execution_id,
        plan:        data.steps,
        results:     data.execution.steps,
        status:      data.execution.overall_status,
      });
      setFinalizeReady(false);

      // Obtener metadata del flujo
      const flowData = await fetcher(`/api/flows/${data.flow_id}`, { method: 'GET' });
      setFlowMeta(flowData);

      // ✨ NEW: Capturar datos del workflow para poder guardarlo
      if (data.steps && data.steps.length > 0) {
        setLastWorkflowData({
          steps: data.steps,
          inputs: data.inputs || {},
          outputs: data.execution?.outputs || {},
          executionId: data.execution_id,
          status: data.execution?.overall_status
        });
        setLastUserMessage(lastUserMessageRef.current || '');
      }
    } catch (err) {
      console.error('[ChatView] Error en confirmFinalize:', err);

      // Si es error de API con detail, mostrarlo
      if (
        err &&
        typeof err === 'object' &&
        Array.isArray(err.detail)
      ) {
        console.error('[ChatView] Error de API en finalize:', err.detail);
      }
    }
  }, [chatHistory, chatId]);

  // ✨ NEW: Manejar guardado de workflow
  const handleSaveWorkflow = () => {
    if (lastWorkflowData) {
      setShowSaveWorkflowModal(true);
    }
  };

  // 🔄 SAME LOGIC AS WORKFLOWCARD: Handle toggle using workflows hook
  const handleWorkflowToggle = async () => {
    if (!currentWorkflowId) return;
    
    try {
      setIsModifyingWorkflow(true);
      const newState = !localWorkflowActive;
      
      console.log('🔧 CHAT TOGGLE: Before toggle - localWorkflowActive:', localWorkflowActive);
      
      // 🚀 INSTANT UPDATE: Update UI immediately (same as WorkflowCard)
      setLocalWorkflowActive(newState);
      
      const result = await toggleWorkflowActive(currentWorkflowId, newState);
      console.log('🔧 CHAT TOGGLE: After toggle - result:', result);
      
      // The global state is already updated in useWorkflows with optimistic update
      // The useEffect will sync if there are differences
      
    } catch (error) {
      console.error('Error toggling workflow in chat:', error);
      // 🔄 REVERT: If failed, revert local state (same as WorkflowCard)
      setLocalWorkflowActive(!newState);
      alert(`Error ${localWorkflowActive ? 'desactivando' : 'activando'} workflow: ${error.message}`);
    } finally {
      setIsModifyingWorkflow(false);
    }
  };

  // 🆕 NEW: Handle workflow decisions via Bridge Service
  const handleWorkflowDecision = async (decision, workflowData = null) => {
    try {
      setIsModifyingWorkflow(true);
      
      console.log(`🎯 Processing workflow decision: ${decision}`);
      
      // Use provided workflowData or fallback to lastWorkflowData
      const targetWorkflow = workflowData || lastWorkflowData;
      
      if (!targetWorkflow) {
        throw new Error('No workflow data available');
      }
      
      const response = await fetcher('/api/chat/workflow-decision', {
        method: 'POST',
        body: {
          decision: decision,
          chat_id: chatId,
          workflow_context: {
            workflow_data: targetWorkflow,
            conversation: sanitizeConversation(chatHistory)
          }
        }
      });

      if (response.success) {
        console.log(`✅ Workflow ${decision} successful:`, response);
        
        // 🔧 FIX: Add response with complete state information
        const messageData = {
          status: decision === 'save' ? 'save_workflow' : 
                  decision === 'activate' ? 'activate_workflow' : 
                  decision === 'deactivate' ? 'save_workflow' : 
                  decision === 'execute' ? 'execute_workflow' : 'success',
          metadata: {
            action_performed: decision === 'save' ? 'save' : 
                            decision === 'activate' ? 'save_and_activate' : 
                            decision === 'deactivate' ? 'deactivate' :
                            decision === 'execute' ? 'execute_now' : decision,
            workflow_id: response.workflow_id,
            execution_id: response.execution_id,
            is_active: decision === 'activate' ? true : decision === 'deactivate' ? false : undefined
          },
          steps: response.steps || [],
          workflow_id: response.workflow_id,
          execution_id: response.execution_id
        };
        
        // 🔧 FIX: Add response message to chat with structured data
        addAssistantMessage(chatId, response.message, messageData);
        
        // Specific actions based on decision type
        if (decision === 'execute') {
          console.log('🚀 Workflow executed, execution_id:', response.execution_id);
        } else if (decision === 'save') {
          console.log('💾 Workflow saved, workflow_id:', response.workflow_id);
        } else if (decision === 'activate') {
          console.log('🔄 Workflow activated, workflow_id:', response.workflow_id);
        } else if (decision === 'deactivate') {
          console.log('🔄 Workflow deactivated, workflow_id:', response.workflow_id);
        }
        
      } else {
        throw new Error(response.message || 'Failed to process workflow decision');
      }
      
    } catch (error) {
      console.error('❌ Error processing workflow decision:', error);
      addAssistantMessage(chatId, 
        `❌ Error procesando la decisión: ${error.message}`,
        { status: 'error', metadata: { error: error.message } }
      );
    } finally {
      setIsModifyingWorkflow(false);
    }
  };

  // ✨ NEW: Handle workflow modification (let LLM decide everything)
  const handleWorkflowModification = async (userMsg) => {
    if (!workflowForReview) return;
    
    setIsModifyingWorkflow(true);
    
    try {
      const data = await fetcher('/api/chat/modify-workflow', {
        method: 'POST',
        body: {
          session_id: chatId,
          message: userMsg,
          current_workflow: workflowForReview,
          conversation: sanitizeConversation(chatHistory)
        }
      });

      // Update the workflow for review if LLM made changes
      if (data.steps) {
        const updatedWorkflow = {
          ...workflowForReview,
          steps: data.steps,
          metadata: data.metadata || workflowForReview.metadata
        };
        setWorkflowForReview(updatedWorkflow);
      }
      
      // 🚨 CRITICAL FIX: Use addAssistantMessage to avoid API call - this is just UI display
      if (data.reply) {
        useChatStore.getState().addAssistantMessage(chatId, data.reply, data);
      }
      
    } catch (err) {
      console.error('[ChatView] Error modifying workflow:', err);
      addAssistantMessage(chatId, 
        'Error procesando tu mensaje. Por favor intenta de nuevo.',
        { status: 'error' }
      );
    } finally {
      setIsModifyingWorkflow(false);
    }
  };


  const handleWorkflowSaved = (savedWorkflow) => {
    console.log('Workflow saved successfully:', savedWorkflow);
    setShowSaveWorkflowModal(false);
    
    // Mostrar notificación de éxito (opcional)
    alert(`✅ Workflow "${savedWorkflow.name}" guardado exitosamente!`);
  };

  // 6️⃣ Limpiar parámetro “?oauth=success” en la URL al montar
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('oauth') === 'success') {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // 7️⃣ Escuchar mensajes desde ventana emergente OAuth
  useEffect(() => {
    const handleMessage = async (evt) => {
      console.log('[ChatView] Window message received:', evt.data, 'from origin:', evt.origin);
      if (evt.origin !== window.origin) return;
      if (evt.data?.oauth === 'success') {
        console.log('[ChatView] OAuth success message received, starting post-OAuth flow...');
        if (popupRef.current && !popupRef.current.closed) {
          popupRef.current.close();
        }
        setShowOAuthButton(false);
        
        // 🔥 NEW: Smart Forms flow after OAuth success
        await handlePostOAuthFlow();
      }
    };

    // 🔥 NEW: Handle Smart Forms flow after OAuth completion
    const handlePostOAuthFlow = async () => {
      // Prevent multiple simultaneous executions
      if (isProcessingRef.current) {
        console.log('[ChatView] Already processing OAuth flow, skipping...');
        return;
      }
      
      isProcessingRef.current = true;
      try {
        console.log('[ChatView] OAuth completed, starting Smart Forms flow...');
        
        // Get current workflow steps that need parameter discovery
        const currentSteps = workflowForReview?.steps || selectedNodes || [];
        
        if (currentSteps.length === 0) {
          console.log('[ChatView] No steps available for Smart Forms, letting QYRAL AI continue naturally');
          // Don't resend - let QYRAL AI continue with her discovery tools
          return;
        }

        // Process each step for Smart Forms
        for (const step of currentSteps) {
          const handlerName = step.action_name || step.name;
          if (!handlerName) continue;

          console.log(`[ChatView] Processing Smart Forms for handler: ${handlerName}`);

          // 1. Check if this handler supports Smart Forms
          const smartFormCheck = await checkSmartFormSupport(handlerName);
          
          if (!smartFormCheck.use_smart_form) {
            console.log(`[ChatView] Handler ${handlerName} doesn't support Smart Forms, skipping...`);
            continue;
          }

          // 2. Analyze parameters (discovery happens here in backend)
          const analysis = await analyzeParameters(handlerName, {});
          
          if (analysis.can_execute) {
            console.log(`[ChatView] Handler ${handlerName} can execute without additional parameters`);
            continue;
          }

          // 3. Get form for missing parameters
          if (analysis.missing_params?.length > 0) {
            console.log(`[ChatView] Handler ${handlerName} needs ${analysis.missing_params.length} additional parameters`);
            
            const formSchema = await getMissingParametersForm(handlerName, {});
            
            if (formSchema) {
              // Store context for Smart Form submission
              setCurrentNode(step.node_id);
              setCurrentAction(step.action_id);
              setFormSchemaEndpoint(null); // Mark as Smart Form
              setShowDynamicForm(true);
              
              // Store Smart Form context
              window.smartFormContext = {
                handlerName,
                discoveredParams: {},
                formSchema,
                step
              };
              
              return; // Wait for user input
            }
          }
        }

        // If no Smart Forms needed, let QYRAL AI continue naturally
        console.log('[ChatView] No Smart Forms needed, letting QYRAL AI continue with discovery');
        // Don't resend - let QYRAL AI continue with her discovery tools
        setCurrentNodeIndex(i => i + 1);

      } catch (error) {
        console.error('[ChatView] Error in Smart Forms flow:', error);
        // Don't fallback to resend - let QYRAL AI handle the continuation
        console.log('[ChatView] Letting QYRAL AI continue naturally after Smart Forms error');
        setCurrentNodeIndex(i => i + 1);
      } finally {
        // Always reset processing flag
        isProcessingRef.current = false;
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // 8️⃣ Manejar nodos pendientes de orquestación
  useEffect(() => {
    if (pendingNodes.length > 0 && currentNodeIndex < pendingNodes.length) {
      const node = pendingNodes[currentNodeIndex];
      setFormSchemaEndpoint(
        `${node.schemaEndpoint}?node_id=${node.node_id}&action_id=${node.action_id}`
      );
      setCurrentNode(node.node_id);
      setCurrentAction(node.action_id);
      setShowDynamicForm(true);
    }
  }, [pendingNodes, currentNodeIndex]);

  // 9️⃣ Finalizar automáticamente cuando todos los nodos estén listos - OPTIMIZED
  useEffect(() => {
    let timeoutId;
    
    if (pendingNodes.length > 0 && 
        currentNodeIndex >= pendingNodes.length && 
        !isAutoFinalizing) {
      
      setIsAutoFinalizing(true);
      
      timeoutId = setTimeout(async () => {
        try {
          const data = await fetcher('/api/chat/finalize', {
            method: 'POST',
            body: {
              session_id: chatId,
              message: '',
              conversation: sanitizeConversation(chatHistory),
            },
          });

          setWorkflow({
            executionId: data.execution_id,
            plan: data.steps,
            results: data.execution.steps,
            status: data.execution.overall_status,
          });
          setFinalizeReady(false);

          // Obtener metadata del flujo
          if (data.flow_id) {
            const flowData = await fetcher(`/api/flows/${data.flow_id}`, { method: 'GET' });
            setFlowMeta(flowData);
          }

          // Capturar datos del workflow para poder guardarlo
          if (data.steps && data.steps.length > 0) {
            setLastWorkflowData({
              steps: data.steps,
              inputs: data.inputs || {},
              outputs: data.execution?.outputs || {},
              executionId: data.execution_id,
              status: data.execution?.overall_status
            });
            setLastUserMessage(lastUserMessageRef.current || '');
          }
          
          setPendingNodes([]);
          setCurrentNodeIndex(0);
        } catch (err) {
          console.error('[ChatView] Error en autoFinalize:', err);
        } finally {
          setIsAutoFinalizing(false);
        }
      }, 100);
    }
    
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [currentNodeIndex, pendingNodes.length, isAutoFinalizing]);

  // 🔟 Listen for pending service selection from store
  useEffect(() => {
    const checkPendingServiceSelection = () => {
      if (window.pendingServiceSelection && window.pendingServiceSelection.chatId === chatId) {
        console.log('🎯 Detected pending service selection:', window.pendingServiceSelection);
        
        setServiceSuggestions(window.pendingServiceSelection.serviceGroups);
        setShowServiceSelection(true);
        
        // Clear the pending selection
        window.pendingServiceSelection = null;
      }
    };
    
    // Check immediately and also poll for changes
    checkPendingServiceSelection();
    const interval = setInterval(checkPendingServiceSelection, 100);
    
    return () => clearInterval(interval);
  }, [chatId]);

  // 🔟 Envío de datos de formulario de parámetros
  const handleFormSubmit = async (formData) => {
    setShowDynamicForm(false);

    // ✨ NEW: Handle Smart Forms submission (direct to QYRAL AI)
    if (formSchemaEndpoint === null && window.smartFormContext?.isSmartForm) {
      try {
        console.log('[ChatView] Submitting Smart Form with data:', formData);
        console.log('[ChatView] Smart Form context:', window.smartFormContext);
        
        // Send form data directly to QYRAL AI via chat API
        const smartFormMessage = `Completé la información requerida: ${JSON.stringify(formData)}`;
        
        // 🔧 FIX: Solo enviar un mensaje, no dos
        // El sendMessage ya maneja la adición del mensaje del usuario automáticamente
        await sendMessage(smartFormMessage);
        
        // Clear Smart Form context
        window.smartFormContext = null;
        
      } catch (error) {
        console.error('[ChatView] Error submitting Smart Form:', error);
        addAssistantMessage(chatId, 
          `❌ Error enviando formulario: ${error.message}`,
          { status: 'error' }
        );
        window.smartFormContext = null;
      }
      
      return;
    }

    // 🔥 LEGACY: Handle Smart Forms submission (API-based)
    if (formSchemaEndpoint === null && window.smartFormContext) {
      try {
        console.log('[ChatView] Submitting Smart Form with data:', formData);
        
        const { handlerName, discoveredParams, step } = window.smartFormContext;
        
        // Execute with combined parameters using Smart Forms API
        const result = await executeWithUserInput(
          handlerName,
          discoveredParams,
          formData,
          {} // credentials would be passed here if needed
        );
        
        console.log('[ChatView] Smart Form execution result:', result);
        
        // Add execution result to chat
        if (result.success) {
          addAssistantMessage(chatId, 
            `✅ ${step.action_name || handlerName} ejecutado exitosamente!`,
            { status: 'success', result }
          );
        } else {
          addAssistantMessage(chatId, 
            `❌ Error ejecutando ${step.action_name || handlerName}: ${result.error || 'Error desconocido'}`,
            { status: 'error', error: result.error }
          );
        }
        
        // Clear Smart Form context
        window.smartFormContext = null;
        
        // Continue with next step
        setCurrentNodeIndex(i => i + 1);
        
      } catch (error) {
        console.error('[ChatView] Error executing Smart Form:', error);
        addAssistantMessage(chatId, 
          `❌ Error ejecutando acción: ${error.message}`,
          { status: 'error' }
        );
        window.smartFormContext = null;
      }
      
      return;
    }

    // Traditional form handling (legacy)
    const formBlock = JSON.stringify({
      form: {
        node:   currentNode,
        action: currentAction,
        params: formData,
      },
    });
    await sendMessage(formBlock);

    const node = pendingNodes[currentNodeIndex];
    if (node?.requiresOAuth) {
      setOauthService(node.oauthProvider);
      setOauthSchemaEndpoint(node.schemaEndpoint);
      setShowOAuthButton(true);
    } else {
      setCurrentNodeIndex(i => i + 1);
    }
  };

  // — Renderizado de la UI —
  return (
    <div className="flex flex-col h-screen bg-gradient-main">
      {/* Header - Compacto */}
      <div className="glass border-b border-primary p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <button 
                onClick={() => route('/', true)}
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
            <button className="btn-primary px-2 py-1.5 rounded-lg text-xs font-medium">
              Configurar
            </button>
            <button 
              onClick={() => setShowSaveWorkflowModal(true)}
              className={`btn-glass px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                !isWorkflowReady ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/20'
              }`}
              disabled={!isWorkflowReady || isModifyingWorkflow}
              title={!isWorkflowReady ? 'Espera a que el workflow esté listo' : 'Guardar workflow'}
            >
              {buttonStates.save}
            </button>
            {/* Switch tipo toggle para activar/desactivar */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">Estado:</span>
              <div className="flex items-center gap-1">
                <span className={`text-xs font-medium ${
                  localWorkflowActive ? 'text-green-400' : 'text-red-400'
                }`}>
                  {localWorkflowActive ? '🟢' : '🔴'}
                </span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localWorkflowActive}
                    onChange={() => {
                      if (currentWorkflowId && !isModifyingWorkflow) {
                        handleWorkflowToggle();
                      } else if (isWorkflowReady && !isModifyingWorkflow) {
                        // Fallback to old logic for workflows not yet saved
                        const currentlyActive = lastResponse?.metadata?.is_active || buttonStates.activate.includes('✓');
                        handleWorkflowDecision(currentlyActive ? 'deactivate' : 'activate');
                      }
                    }}
                    disabled={!isWorkflowReady || isModifyingWorkflow}
                    className="sr-only peer"
                  />
                  <div className={`w-8 h-4 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-purple-500 ${
                    !isWorkflowReady || isModifyingWorkflow ? 'opacity-50 cursor-not-allowed' : ''
                  }`}></div>
                </label>
              </div>
            </div>
            <button 
              onClick={() => isWorkflowReady && handleWorkflowDecision('execute')}
              className={`btn-glass px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                !isWorkflowReady ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-500/20'
              }`}
              disabled={!isWorkflowReady || isModifyingWorkflow}
              title={!isWorkflowReady ? 'Espera a que el workflow esté listo' : 'Ejecutar workflow inmediatamente'}
            >
              {buttonStates.execute}
            </button>
            {mode === 'ai' && (
              <button 
                onClick={() => setShowDeployModal(true)}
                className="btn-glass px-2 py-1.5 rounded-lg text-xs font-medium"
              >
                Deploy
              </button>
            )}
          </div>
        </div>
      </div>
      
      {simpleQuestions.length > 0 && (
        <ClarifyModal
          questions={simpleQuestions}
          onSubmit={(answers) => {
            sendMessage(JSON.stringify({ clarifyAnswers: answers, node_ids: [] }));
            setSimpleQuestions([]);
          }}
          onCancel={() => setSimpleQuestions([])}
        />
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {(isNewChat || chatHistory.length === 0) && (
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
                onClick={() => setMessage('Quiero automatizar el envío de emails cuando reciba nuevos leads')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">📧</div>
                <div className="font-medium text-text-primary text-sm mb-1">Email Automation</div>
                <div className="text-xs text-text-secondary">Emails automáticos para nuevos leads</div>
              </div>
              
              <div 
                onClick={() => setMessage('Ayúdame a conectar Slack con Google Drive para notificaciones')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">🔗</div>
                <div className="font-medium text-text-primary text-sm mb-1">App Integration</div>
                <div className="text-xs text-text-secondary">Conecta Slack con Google Drive</div>
              </div>
              
              <div 
                onClick={() => setMessage('Quiero programar reportes automáticos cada lunes')}
                className="glass-light p-3 rounded-xl cursor-pointer hover:scale-105 transition-all duration-200 text-left"
              >
                <div className="text-lg mb-1">📊</div>
                <div className="font-medium text-text-primary text-sm mb-1">Scheduled Reports</div>
                <div className="text-xs text-text-secondary">Reportes automáticos semanales</div>
              </div>
              
              <div 
                onClick={() => setMessage('Ayúdame a automatizar la gestión de mi calendario')}
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
        )}
        
        {!isNewChat && chatHistory
          .filter(msg => {
            // ✅ FINAL UI FILTER: Extra safety check for UI rendering
            if (msg.role === 'system') return false;
            if (msg.isSelectionFeedback || msg.skipBackend) return false;
            if (!msg.content || !msg.content.trim()) return false;
            return true;
          })
          .map((msg, i) => (
          <div
            key={`${msg.timestamp || Date.now()}-${i}`}
            className={`flex gap-4 items-start animate-fadeInUp ${
              msg.role === 'user' ? 'flex-row-reverse' : ''
            }`}
          >
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
              msg.role === 'user' 
                ? 'surface-elevated text-white' 
                : 'glass text-accent'
            }`}>
              {msg.role === 'user' ? 'TÚ' : 'AI'}
            </div>
            <div className={`max-w-[70%] ${
              msg.role === 'user' ? 'glass surface-elevated border-accent' : 'glass-light'
            } p-4 rounded-2xl transition-all duration-300 hover:transform hover:scale-[1.02]`}>
              <div className="text-text-primary leading-relaxed whitespace-pre-wrap">
                {msg.content}
              </div>
              <div className="text-xs text-text-muted mt-2 flex items-center justify-between">
                <span>
                  {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                </span>
                {/* ✅ FIX: Show message status indicators */}
                {msg.role === 'user' && msg.status && (
                  <span className={`ml-2 ${
                    msg.status === 'sending' ? 'text-yellow-500' :
                    msg.status === 'sent' ? 'text-green-500' :
                    msg.status === 'failed' ? 'text-red-500' : ''
                  }`}>
                    {msg.status === 'sending' ? '⏳' :
                     msg.status === 'sent' ? '✓' :
                     msg.status === 'failed' ? '❌' : ''}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {/* Loading state for initial message processing */}
        {isSendingMessage && (
          <div className="flex gap-4 items-start animate-fadeInUp">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold flex-shrink-0 glass text-accent">
              AI
            </div>
            <div className="max-w-[70%] glass-light p-4 rounded-2xl transition-all duration-300">
              <div className="text-text-primary leading-relaxed flex items-center gap-3">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-accent"></div>
                {chatHistory.length === 0 ? 'Creando workflow...' : 'Procesando solicitud...'}
              </div>
              <div className="text-xs text-text-muted mt-2">
                {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        )}
        
        {/* ✅ DEBUG: Show message count */}
        {process.env.NODE_ENV === 'development' && (
          <div className="text-xs text-gray-500 text-center">
            Mostrando {chatHistory.length} mensajes de {rawChatHistory.length} total
          </div>
        )}
      </div>


      {/* OAuth Requirements Handler */}
      {(() => {
        const lastMessage = chatHistory.length > 0 ? chatHistory[chatHistory.length - 1] : null;
        // Try both chatHistory (raw) and lastResponse (parsed) for oauth_requirements
        const oauthRequirements = lastMessage?.oauth_requirements || lastResponse?.oauth_requirements || [];
        
        console.log('🔍 OAUTH CHECK:', {
          hasLastMessage: !!lastMessage,
          hasOAuthReqs: oauthRequirements.length > 0,
          oauthLength: oauthRequirements.length,
          oauthReqs: oauthRequirements,
          oauthAlreadySatisfied: !!(lastResponse?.metadata?.oauth_already_satisfied)
        });
        
        // ✅ REMOVED: oauth_already_satisfied handler to prevent duplicate messages
        // This was causing automatic message resends that duplicated the entire flow
        
        return oauthRequirements.length > 0;
      })() && (
        <OAuthRequirementHandler
          oauthRequirements={lastResponse?.oauth_requirements || []}
          chatId={chatId}
          onAllCompleted={async (completedProviders, authData) => {
            console.log('🎉 ChatView - onAllCompleted callback triggered!');
            console.log('🎉 ChatView - completedProviders:', completedProviders);
            console.log('🎉 ChatView - authData:', authData);
            
            // 🔒 FIX INFINITE LOOP: Solo UNA acción, no múltiples requests paralelos
            console.log('🎉 ChatView - OAuth completion detected, continuing workflow...');
            
            // Check if we should resend message for existing credentials
            if (authData?.shouldResendMessage) {
              console.log('🔄 [ChatView] Existing credentials detected, resending last message');
              resendLastMessage();
              return;
            }
            
            // ✅ FIX: OAuth completed for ALL required services
            console.log('🎉 ALL OAuth services completed:', completedProviders);
            console.log('📤 Injecting OAuth completion as system message (NO UI MESSAGE)...');
            
            try {
              const systemMessage = {
                id: `oauth-success-${Date.now()}`,
                text: `OAuth authentication completed successfully for ${completedProviders.join(', ')}. Continue with workflow execution using the authenticated services.`,
                sender: 'system',
                timestamp: Date.now(),
                isOAuthSuccess: true
              };
              
              // ✅ FIX: NO UI message - only send to backend to avoid duplication
              console.log('💫 NO UI MESSAGE - sending directly to backend to avoid duplication');
              
              // Trigger workflow continuation with OAuth context via API
              const response = await fetcher.post('/api/chat', {
                message: '', // Empty user message - system message carries the context
                chat_id: chatId,
                oauth_completed: completedProviders,
                system_message: systemMessage.text,
                continue_workflow: true,
                workflow_type: mode === 'ai' ? 'agent' : 'classic'
              });
              
              if (response.workflow_id || response.reply) {
                console.log('✅ Workflow continuation initiated successfully');
                
                // ✅ FIX: Backend response is automatically added by fetcher/store
                // NO manual message addition needed - prevents duplication
                console.log('💫 Backend will handle response message - no manual addition');
              }
              
              console.log('✅ OAuth system message injection completed');
            } catch (error) {
              console.error('❌ Error injecting OAuth system message:', error);
              // ✅ FIX: Show error in UI but DON'T send duplicate message
              addAssistantMessage(chatId, `❌ Error procesando OAuth completion: ${error.message}`, {
                status: 'error',
                metadata: { oauth_error: true }
              });
            }
          }}
          onError={(error, requirement) => {
            console.error('OAuth error:', error, requirement);
          }}
        />
      )}

      {selectedNodes.length > 0 && (
        <div className="mb-4 p-4 bg-surface text-text-primary rounded">
          <h4 className="text-lg font-bold">Nodos seleccionados:</h4>
          <ul>
            {selectedNodes.map((node) => (
              <li key={`${node.node_id}-${node.action_id}`}>
                {node.node_id} → {node.action_id}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Input Area - Más prominente */}
      <div className="glass border-t border-primary p-4 bg-gradient-to-r from-glass-dark to-glass-medium">
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder={isNewChat || chatHistory.length === 0 
                ? "💡 ¡Empieza aquí! Describe qué quieres automatizar..." 
                : "💬 Continúa la conversación o ajusta tu automatización..."
              }
              rows={1}
              className="w-full glass-light rounded-xl px-4 py-3 pr-12 text-sm resize-none focus-ring bg-transparent text-text-primary placeholder-text-secondary min-h-[48px] max-h-[120px] border-2 border-primary focus:border-accent"
              style={{ scrollbarWidth: 'none' }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!message.trim() || isSendingMessage || isCreatingChat}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 btn-primary w-10 h-10 rounded-lg flex items-center justify-center text-lg disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isSendingMessage || isCreatingChat ? '⏳' : '🚀'}
            </button>
          </div>
          
          {finalizeReady && (
            <button
              onClick={confirmFinalize}
              className="btn-glass px-3 py-2 rounded-lg text-sm font-medium text-green-400 border-green-400/30 hover:bg-green-500/10"
            >
              ✅ Finalizar
            </button>
          )}
          
          <button
            onClick={() => setShowCredModal(true)}
            className="btn-glass px-3 py-2 rounded-lg text-sm font-medium"
          >
            🔐 Creds
          </button>
        </div>
      </div>

      {showOAuthButton && (
        <div className="mb-4">
          <button
            onClick={() => {
              popupRef.current = window.open(
                oauthSchemaEndpoint,
                'oauthPopup',
                'width=500,height=600'
              );
            }}
            className="bg-red-500 text-white px-4 py-2 rounded"
          >
            Autorizar {oauthService}
          </button>
        </div>
      )}

      {showDynamicForm && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
          <div className="bg-white p-6 rounded shadow w-96">
            <DynamicForm
              schemaEndpoint={formSchemaEndpoint}
              smartFormSchema={formSchemaEndpoint === null ? window.smartFormContext?.formSchema : null}
              node={currentNode}
              action={currentAction}
              onSubmit={handleFormSubmit}
              onCancel={() => setShowDynamicForm(false)}
            />
          </div>
        </div>
      )}

      {workflow && (
        <div>
          <h3>Plan original:</h3>
          <ul>
            {workflow.plan.map((s) => (
              <li key={s.node_id + s.action_id}>
                {s.node_id} → {s.action_id}
              </li>
            ))}
          </ul>
          <h3>Resultados:</h3>
          <ul>
            {workflow.results.map((r) => (
              <li key={r.node_id + r.action_id}>
                {r.node_id}.{r.action_id}: {r.status}
                {r.error && <span className="text-red-500"> – {r.error}</span>}
              </li>
            ))}
          </ul>
          
          {/* ✨ NEW: Botón para guardar workflow */}
          {lastWorkflowData && (workflow.status === 'success' || workflow.status === 'completed' || workflow.results) && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-green-800 font-medium">Workflow ejecutado exitosamente</h4>
                  <p className="text-green-600 text-sm">
                    Guarda este workflow para reutilizarlo o programarlo
                  </p>
                </div>
                <button
                  onClick={handleSaveWorkflow}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors flex items-center"
                >
                  {buttonStates.save}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {flowMeta && <WorkflowSidePanel flow={flowMeta} onClose={() => setFlowMeta(null)} />}
      <CredentialsManager
        isOpen={showCredModal}
        onClose={() => setShowCredModal(false)}
        chatId={chatId}
      />

      {/* ✨ NEW: Save Workflow Modal */}
      <SaveWorkflowModal
        isOpen={showSaveWorkflowModal}
        onClose={handleWorkflowSaved}
        workflowData={lastWorkflowData}
        userMessage={lastUserMessage}
        chatId={chatId}
      />

      {/* Deploy Agent Modal */}
      <DeployAgentModal
        isOpen={showDeployModal}
        onClose={() => setShowDeployModal(false)}
      />

      {/* ✨ NEW: Service Selection Modal (QYRAL AI + CAG dropdown) */}
      {showServiceSelection && (
        <div className="fixed inset-0 flex items-center justify-center bg-gradient-main/80 backdrop-blur-sm z-50">
          <div className="glass-card rounded-xl shadow-elegant-lg max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b border-primary">
              <h3 className="text-xl font-semibold text-elegant">QYRAL AI encontró múltiples servicios</h3>
            </div>

            {/* Form Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <div className="space-y-6">
              {serviceSuggestions.map((group, groupIndex) => (
                <div key={groupIndex} className="border border-gray-700 bg-gray-800/30 rounded-lg p-4 backdrop-blur-sm">
                  <h4 className="font-medium mb-2 text-gray-100">
                    {group.message || `Servicios de ${group.category}`}
                  </h4>
                  
                  <div className="space-y-2">
                    {group.options?.map((option, optionIndex) => (
                      <label key={optionIndex} className="flex items-start space-x-3 cursor-pointer p-3 hover:surface-card rounded-lg border border-transparent hover:border-accent transition-all duration-200">
                        <input
                          type="radio"
                          name={`group_${groupIndex}`}
                          className="mt-1.5 accent-white"
                          defaultChecked={optionIndex === 0} // Seleccionar el primero por defecto
                          data-node-id={option.node_id}
                          data-category={group.category}
                        />
                        <div className="flex-1">
                          <div className="font-medium text-white">{option.name}</div>
                          {option.description && (
                            <div className="text-sm text-gray-400 mt-1">{option.description}</div>
                          )}
                        </div>
                      </label>
                    )) || (
                      // Legacy format support
                      <label key={groupIndex} className="flex items-start space-x-3 cursor-pointer p-3 hover:surface-card rounded-lg border border-transparent hover:border-accent transition-all duration-200">
                        <input
                          type="checkbox"
                          className="mt-1.5 accent-white"
                          defaultChecked={groupIndex === 0}
                          data-service={group.name}
                        />
                        <div>
                          <div className="font-medium text-white">{group.name}</div>
                          <div className="text-sm text-gray-400 mt-1">{group.reason}</div>
                        </div>
                      </label>
                    )}
                  </div>
                </div>
              ))}
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="px-6 py-4 border-t border-primary flex justify-end space-x-3">
              <button
                onClick={() => setShowServiceSelection(false)}
                className="px-6 py-2.5 surface-card text-subtle border border-surface-border rounded-lg hover:surface-card-hover transition-all duration-200"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  // Obtener servicios seleccionados del nuevo formato
                  const radioButtons = document.querySelectorAll('input[data-node-id]:checked');
                  const checkboxes = document.querySelectorAll('input[data-service]:checked');
                  
                  let selected = [];
                  
                  if (radioButtons.length > 0) {
                    // Nuevo formato con grupos - enviar node_id como string
                    selected = Array.from(radioButtons).map(radio => radio.dataset.nodeId);
                  } else if (checkboxes.length > 0) {
                    // Legacy format
                    selected = Array.from(checkboxes).map(cb => cb.dataset.service);
                  }
                  
                  if (selected.length === 0) {
                    alert('Por favor selecciona al menos un servicio');
                    return;
                  }
                  
                  handleServiceSelection(selected);
                }}
                className="px-6 py-2.5 bg-gradient-to-r from-accent-700 to-accent-800 text-white rounded-lg hover:from-accent-600 hover:to-accent-700 transition-all duration-200 shadow-lg hover:shadow-elegant"
              >
                Continuar con servicios seleccionados
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


