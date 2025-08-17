// Nueva implementación limpia del chat store basada en mejores prácticas 2025
import { create } from 'zustand';
import { API_BASE_URL } from '../config';
import { fetcher } from '../api/fetcher';

const useChatStore = create((set, get) => ({
  // Estado básico
  chats: [],
  activeChatId: null,
  messages: {},
  isLoading: false,
  error: null,
  
  // 🔄 PERSISTENTE: Estado del workflow por chat
  workflowStates: {}, // { chatId: { execution_plan: [], workflow_created: true, metadata: {} } }
  
  // 🔧 RACE CONDITION PREVENTION: Throttle loadChats calls
  _lastLoadChatsCall: 0,
  _loadChatsThrottle: 2000, // 2 seconds minimum between calls

  // Acciones básicas
  setActiveChatId: (chatId) => set({ activeChatId: chatId }),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  clearError: () => set({ error: null }),

  // Crear nuevo chat - BACKUP SESSION LOGIC
  createChat: async (title = '') => {
    set({ isLoading: true, error: null });
    
    try {
      console.log('Creating chat with title:', title);
      // Usar la misma lógica que funcionaba en el backup
      const session = await fetcher('/api/chats/', {
        method: 'POST',
        body: { title: title || 'Nuevo chat' },
      });
      console.log('Chat created successfully:', session);

      const newSession = {
        ...session,
        title: session.title || 'Nuevo chat',
      };

      set(state => ({
        chats: [...state.chats, newSession],
        activeChatId: newSession.session_id,
        messages: {
          ...state.messages,
          [newSession.session_id]: [],
        },
        isLoading: false
      }));

      return newSession;
    } catch (error) {
      console.error('Error creating chat session:', error);
      set({ error: error.message || 'Error creando chat', isLoading: false });
      // En lugar de fallback ID, lanzar error para manejo apropiado
      throw new Error('Failed to create chat session: ' + error.message);
    }
  },

  // Alias para compatibilidad con ChatView actual
  addChat: async (title = '') => {
    const session = await get().createChat(title);
    return session?.session_id;
  },

  // 🧹 CLEAR MESSAGES: Simple function to clear messages when navigating to /chat/
  clearMessagesForNewChat: () => {
    console.log('🧹 CLEARING: Messages cleared for new chat initialization');
    set(state => ({
      activeChatId: null,
      messages: {},
      error: null
    }));
  },

  // ⚡ WORKFLOW MANAGEMENT ACTIONS - DIRECT APPROACH
  executeWorkflowDirect: async (chatId, executionPlan) => {
    set({ isLoading: true, error: null });
    
    try {
      console.log('🚀 Executing workflow DIRECT for chat:', chatId);
      console.log('🎯 Using execution_plan directly:', executionPlan?.length || 0, 'steps');
      
      const response = await fetcher('/api/chat/workflow-decision', {
        method: 'POST',
        body: {
          decision: 'execute',
          chat_id: chatId,
          session_id: chatId,
          execution_plan: executionPlan || []
        }
      });
      
      console.log('✅ Workflow executed successfully:', response);
      
      // Add success message to chat
      const successMessage = {
        id: `success-${Date.now()}`,
        role: 'assistant',
        content: response.message || '✅ Workflow ejecutado exitosamente',
        timestamp: new Date().toISOString(),
        isTemp: false
      };
      
      set(state => ({
        messages: {
          ...state.messages,
          [chatId]: [...(state.messages[chatId] || []), successMessage]
        },
        isLoading: false
      }));
      
      return response;
    } catch (error) {
      console.error('❌ Error executing workflow:', error);
      set({ error: error.message || 'Error ejecutando workflow', isLoading: false });
      throw error;
    }
  },

  saveWorkflowDirect: async (chatId, executionPlan) => {
    set({ isLoading: true, error: null });
    
    try {
      console.log('💾 Saving workflow DIRECT for chat:', chatId);
      console.log('🎯 Using execution_plan directly:', executionPlan?.length || 0, 'steps');
      
      const response = await fetcher('/api/chat/workflow-decision', {
        method: 'POST',
        body: {
          decision: 'save',
          chat_id: chatId,
          session_id: chatId,
          execution_plan: executionPlan || []
        }
      });
      
      console.log('✅ Workflow saved successfully:', response);
      
      // Add success message to chat
      const successMessage = {
        id: `saved-${Date.now()}`,
        role: 'assistant', 
        content: response.message || '💾 Workflow guardado exitosamente',
        timestamp: new Date().toISOString(),
        isTemp: false
      };
      
      set(state => ({
        messages: {
          ...state.messages,
          [chatId]: [...(state.messages[chatId] || []), successMessage]
        },
        isLoading: false
      }));
      
      return response;
    } catch (error) {
      console.error('❌ Error saving workflow:', error);
      set({ error: error.message || 'Error guardando workflow', isLoading: false });
      throw error;
    }
  },

  activateWorkflowDirect: async (chatId, executionPlan) => {
    set({ isLoading: true, error: null });
    
    try {
      console.log('🔄 Activating workflow DIRECT for chat:', chatId);
      console.log('🎯 Using execution_plan directly:', executionPlan?.length || 0, 'steps');
      
      const response = await fetcher('/api/chat/workflow-decision', {
        method: 'POST',
        body: {
          decision: 'activate',
          chat_id: chatId,
          session_id: chatId,
          execution_plan: executionPlan || []
        }
      });
      
      console.log('✅ Workflow activated successfully:', response);
      
      // Add success message to chat
      const successMessage = {
        id: `activated-${Date.now()}`,
        role: 'assistant',
        content: response.message || '🔄 Workflow activado exitosamente',
        timestamp: new Date().toISOString(),
        isTemp: false
      };
      
      set(state => ({
        messages: {
          ...state.messages,
          [chatId]: [...(state.messages[chatId] || []), successMessage]
        },
        isLoading: false
      }));
      
      return response;
    } catch (error) {
      console.error('❌ Error activating workflow:', error);
      set({ error: error.message || 'Error activando workflow', isLoading: false });
      throw error;
    }
  },

  // 🗑️ REMOVED: All extraction methods - using direct approach now
  // No more _extractExecutionPlanFromMessages or _extractWorkflowContext needed

  // Enviar mensaje
  sendMessage: async (chatId, role, content) => {
    // Optimistic update - agregar mensaje inmediatamente
    const tempMessage = {
      id: `temp-${Date.now()}`,
      role,
      content,
      timestamp: new Date().toISOString(),
      isTemp: true
    };

    set(state => ({
      messages: {
        ...state.messages,
        [chatId]: [...(state.messages[chatId] || []), tempMessage]
      },
      isLoading: true,
      error: null
    }));

    try {
      // Obtener estado actual para construir conversación
      const currentState = get();
      const currentMessages = currentState.messages[chatId] || [];
      
      console.log('🚀 Enviando mensaje al backend:', {
        chatId,
        content,
        messagesCount: currentMessages.length
      });
      
      // Obtener workflow_type del modo actual
      const { default: useModeStore } = await import('../stores/modeStore');
      const currentMode = useModeStore.getState().mode;
      
      // Usar el endpoint correcto del backend con TODOS los campos requeridos
      const result = await fetcher('/api/chat', {
        method: 'POST',
        body: {
          session_id: chatId,
          message: content,
          conversation: currentMessages
            .filter(msg => !msg.isTemp)
            .map(msg => ({ role: msg.role, content: msg.content })),
          workflow_type: currentMode === 'ai' ? 'agent' : 'classic'  // CAMPO REQUERIDO
        }
      });
      
      console.log('✅ Respuesta del backend:', result);
      
      // Agregar mensaje del usuario + respuesta del asistente si existe
      set(state => {
        const newMessages = [
          ...state.messages[chatId].filter(msg => msg.id !== tempMessage.id),
          // Mensaje del usuario
          {
            id: `user-${Date.now()}`,
            role: 'user',
            content,
            timestamp: new Date().toISOString()
          }
        ];

        // Agregar respuesta del asistente si existe
        if (result && result.reply) {
          newMessages.push({
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: result.reply,
            timestamp: new Date().toISOString(),
            // Guardar datos completos para workflow management
            metadata: {
              session_id: result.session_id,
              status: result.status,
              workflow_action: result.workflow_action,
              oauth_requirements: result.oauth_requirements,
              service_suggestions: result.service_suggestions,
              // 🎯 Incluir SmartForm data del backend
              smart_forms_required: result.smart_forms_required,
              smart_form: result.smart_form,
              // 🔄 REQUIRED: execution_plan needed for fallback recovery
              execution_plan: result.execution_plan || []
            }
          });
        }

        return {
          messages: {
            ...state.messages,
            [chatId]: newMessages
          },
          isLoading: false
        };
      });

      // 🏗️ ARQUITECTURA LIMPIA: Always load workflow context from WorkflowContextService
      // 🚀 OPTIMIZADO: Solo cuando backend indica enhanced_workflow = true
      if (result.enhanced_workflow) {
        console.log('🔍 CHATSTORE: Enhanced workflow detected, loading context from WorkflowContextService');
        try {
          const workflowContext = await get()._extractWorkflowContext([], chatId);
          if (workflowContext.steps && workflowContext.steps.length > 0) {
            console.log(`🎯 CHATSTORE: Loaded ${workflowContext.steps.length} steps from WorkflowContextService`);
            // Update the message metadata with real steps
            set((state) => {
              const messages = [...(state.messages[chatId] || [])];
              const lastMessage = messages[messages.length - 1];
              if (lastMessage && lastMessage.metadata) {
                lastMessage.metadata.steps = workflowContext.steps;
                lastMessage.metadata.workflow_context_loaded = true; // Flag para debugging
              }
              return { messages: { ...state.messages, [chatId]: messages } };
            });
          }
        } catch (error) {
          console.error('🔥 Error loading workflow context:', error);
        }
      } else if (result.hasOwnProperty('enhanced_workflow')) {
        // 🔍 DEBUG: Log cuando NO hay enhanced_workflow para debugging
        console.log('🔍 CHATSTORE: No enhanced_workflow detected - backend indicates no workflow changes');
      }

      // 🎯 SmartForm Detection - basado en backup legacy
      console.log('🔍 CHATSTORE: Checking for smart forms...', {
        smart_forms_required: result.smart_forms_required,
        has_smart_form: !!result.smart_form,
        smart_form_title: result.smart_form?.title,
        smart_form_fields: result.smart_form?.fields?.length || 0
      });
      
      if (result.smart_forms_required && result.smart_form) {
        console.log('🎉 CHATSTORE: Smart form detected! Setting up context:', {
          title: result.smart_form.title,
          fields: result.smart_form.fields?.length || 0,
          sections: result.smart_form.sections?.length || 0
        });
        
        window.smartFormContext = {
          formSchema: result.smart_form,
          isSmartForm: true,
          backendData: result
        };
        
        // Trigger smart form display - signal to ChatView that smart form is ready
        console.log('🚀 CHATSTORE: Dispatching smartFormReady event');
        window.dispatchEvent(new CustomEvent('smartFormReady', { 
          detail: { 
            chatId, 
            smartForm: result.smart_form,
            backendData: result
          } 
        }));
      } else {
        console.log('⚠️ CHATSTORE: No smart forms detected - requirements:', result.smart_forms_required, 'form:', !!result.smart_form);
      }

      // 🔐 OAuth Requirements Detection - Check for oauth_requirements and trigger CredentialsManager
      console.log('🔍 CHATSTORE: Checking for OAuth requirements...', {
        oauth_requirements: result.oauth_requirements,
        oauth_count: result.oauth_requirements?.length || 0,
        status: result.status
      });
      
      if (result.oauth_requirements && result.oauth_requirements.length > 0) {
        console.log('🔐 CHATSTORE: OAuth requirements detected! Triggering credentials modal:', {
          count: result.oauth_requirements.length,
          requirements: result.oauth_requirements
        });
        
        // Trigger credentials manager display - signal to ChatView that OAuth is needed
        console.log('🚀 CHATSTORE: Dispatching oauthRequirementsDetected event');
        window.dispatchEvent(new CustomEvent('oauthRequirementsDetected', { 
          detail: { 
            chatId, 
            oauthRequirements: result.oauth_requirements,
            backendData: result
          } 
        }));
      } else {
        console.log('⚠️ CHATSTORE: No OAuth requirements detected');
      }

      // 🔄 TRIGGER: Auto-cache execution_plan para persistencia
      if (result && result.execution_plan && result.execution_plan.length > 0) {
        try {
          const workflowCache = {
            execution_plan: result.execution_plan,
            workflow_created: true,
            timestamp: Date.now(),
            metadata: {
              session_id: result.session_id,
              status: result.status
            }
          };
          localStorage.setItem(`workflow_${chatId}`, JSON.stringify(workflowCache));
          console.log('🔄 TRIGGER: Auto-cached execution_plan para chat:', chatId, '- steps:', result.execution_plan.length);
        } catch (error) {
          console.error('🔄 TRIGGER: Error caching execution_plan:', error);
        }
      }

      // 🚀 DIRECT APPROACH: Return full result for ChatView to use directly
      return result;
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Remover mensaje temporal en caso de error
      set(state => ({
        messages: {
          ...state.messages,
          [chatId]: state.messages[chatId].filter(msg => msg.id !== tempMessage.id)
        },
        error: error.message || 'Error enviando mensaje',
        isLoading: false
      }));
      
      return null; // Return null on error so ChatView can handle it
    }
  },

  // Cargar sesiones - BACKUP SESSION LOGIC
  loadChats: async () => {
    // 🔧 THROTTLE: Prevent race conditions from multiple rapid calls
    const now = Date.now();
    const currentState = get();
    
    if (now - currentState._lastLoadChatsCall < currentState._loadChatsThrottle) {
      console.log('🔄 THROTTLED: loadChats called too soon, skipping...');
      return currentState.chats;
    }
    
    set({ _lastLoadChatsCall: now });
    
    try {
      console.log('🔄 Fetching chats from server...');
      
      // Increased timeout to 10 seconds
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      const sessions = await fetcher('/api/chats/', { 
        method: 'GET',
        signal: controller.signal 
      });
      
      clearTimeout(timeoutId);
      
      console.log('✅ Fetched chats from server:', sessions?.length || 0, 'chats');
      
      // ✅ FIX: Only update sessions, preserve chat messages to avoid losing loaded messages
      const currentState = get();
      
      // ✅ CHAT SELECTION: Only auto-select first chat if current activeChatId still exists
      let newActiveChatId = null;
      if (sessions && sessions.length > 0) {
        // If current activeChatId still exists in sessions, keep it
        if (currentState.activeChatId && sessions.some(s => s.session_id === currentState.activeChatId)) {
          newActiveChatId = currentState.activeChatId;
        }
        // Don't auto-select first chat - let user manually select or send first message
      }
      
      set({
        chats: sessions || [],
        activeChatId: newActiveChatId,
        // ✅ FIX: Preserve existing chat messages instead of resetting
        messages: currentState.messages // Keep existing messages
      });
      
      return sessions;
    } catch (err) {
      console.error('❌ Error fetching chat sessions:', err);
      
      // Don't clear on error - keep what we have
      // Only clear if it's a 401 or auth error
      if (err?.status === 401) {
        set({
          chats: [],
          activeChatId: null,
          messages: {}
        });
      } 
      // Let calling component handle isLoading state
      
      throw err;
    }
  },

  // Alias para compatibilidad - BACKUP SESSION LOGIC
  fetchSessions: async () => {
    return await get().loadChats();
  },

  // Cargar mensajes de un chat - BACKUP SESSION LOGIC
  loadMessages: async (chatId) => {
    try {
      // ✅ FIX: Check if messages are already loaded to avoid unnecessary fetches
      const currentMessages = get().messages[chatId];
      if (currentMessages && currentMessages.length > 0) {
        console.log('📋 Messages already loaded for chat:', chatId, '- count:', currentMessages.length);
        return currentMessages;
      }
      
      console.log('🔄 Fetching messages for chat:', chatId);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // ✅ FIX: Increase timeout to 30s
      
      const messages = await fetcher(`/api/chats/${chatId}/messages`, {
        method: 'GET',
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      console.log('✅ Fetched messages for chat:', chatId, '- total:', messages?.length || 0);
      
      // 🔧 BEST PRACTICE 2025: Merge server messages with optimistic updates
      set(state => {
        const currentMessages = state.messages[chatId] || [];
        const serverMessages = messages || [];
        
        // Keep any optimistic messages (isTemp: true) that haven't been confirmed by server
        const optimisticMessages = currentMessages.filter(msg => msg.isTemp === true);
        
        // Merge: server messages + optimistic messages (avoiding duplicates by timestamp)
        const mergedMessages = [
          ...serverMessages,
          ...optimisticMessages.filter(optimistic => 
            !serverMessages.some(server => 
              Math.abs(new Date(server.timestamp) - new Date(optimistic.timestamp)) < 5000 // 5 second window
            )
          )
        ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        console.log('🔄 MERGE: Server messages:', serverMessages.length, 'Optimistic:', optimisticMessages.length, 'Final:', mergedMessages.length);
        
        return {
          messages: {
            ...state.messages,
            [chatId]: mergedMessages,
          }
        };
      });
      
      return messages;
    } catch (err) {
      console.error('❌ Error fetching messages for', chatId, err);
      
      // ✅ FIX: Only set empty array if there are NO existing messages (preserve existing messages on error)
      const existingMessages = get().messages[chatId];
      if (!existingMessages || existingMessages.length === 0) {
        console.log('📝 Setting empty array for chat:', chatId, '(no existing messages)');
        set(state => ({
          messages: {
            ...state.messages,
            [chatId]: [],
          }
        }));
      } else {
        console.log('💾 Preserving existing messages for chat:', chatId, '- count:', existingMessages.length);
        // Don't touch isLoading state - let calling component handle it
      }
      
      throw err;
    }
  },

  // Alias para compatibilidad - BACKUP SESSION LOGIC
  fetchMessages: async (chatId) => {
    return await get().loadMessages(chatId);
  },

  // Actualizar chat (renombrar)
  updateChat: async (chatId, updateData) => {
    try {
      // Optimistic UI update
      set(state => ({
        chats: state.chats.map(chat => 
          chat.session_id === chatId 
            ? { ...chat, ...updateData }
            : chat
        )
      }));

      // Make API call to update on server
      const response = await fetcher(`/api/chats/${chatId}`, {
        method: 'PATCH',
        body: updateData
      });

      console.log('✅ Chat updated successfully:', chatId, updateData);
      return response;
    } catch (error) {
      console.error('❌ Error updating chat:', error);
      
      // Revert optimistic update on error
      get().loadChats(); // Reload from server
      
      set({ error: error.message || 'Error actualizando chat' });
      throw error;
    }
  },

  // Borrar chat
  deleteChat: async (chatId) => {
    try {
      const currentState = get();
      const chatExists = currentState.chats.some(chat => chat.session_id === chatId);
      
      if (!chatExists) {
        console.log('Chat already removed from UI:', chatId);
        return;
      }

      const wasActiveChat = currentState.activeChatId === chatId;

      // Optimistic UI update - remove immediately for better UX
      set(state => ({
        chats: state.chats.filter(chat => chat.session_id !== chatId),
        messages: Object.fromEntries(
          Object.entries(state.messages).filter(([id]) => id !== chatId)
        ),
        activeChatId: state.activeChatId === chatId ? null : state.activeChatId
      }));

      // 🔧 RESTORE BACKUP BEHAVIOR: Redirect to temporal chat if active chat was deleted
      if (wasActiveChat) {
        console.log('🔄 Active chat deleted, redirecting to temporal chat /chat/...');
        // Dynamic import to avoid circular dependencies
        const { route } = await import('preact-router');
        route('/chat', true);
      }

      // Make API call to delete from server
      console.log(`🗑️ Attempting to delete chat ${chatId} from server...`);
      const response = await fetcher(`/api/chats/${chatId}`, { 
        method: 'DELETE' 
      });

      console.log('✅ Chat deleted successfully from server:', chatId);
      
      // Force sync - refetch from server to ensure consistency
      setTimeout(() => {
        get().loadChats().catch(console.error);
      }, 100);
      
      return response;
    } catch (error) {
      console.error('❌ Error deleting chat session from server:', error);
      
      // Revert optimistic update on error
      get().loadChats(); // Reload from server
      
      set({ error: error.message || 'Error eliminando chat' });
      throw error;
    }
  },

  // 🔄 WORKFLOW STATE MANAGEMENT: Persistir estado del workflow
  setWorkflowState: (chatId, workflowState) => set(state => ({
    workflowStates: {
      ...state.workflowStates,
      [chatId]: workflowState
    }
  })),
  
  getWorkflowState: (chatId) => {
    const state = get();
    return state.workflowStates[chatId] || null;
  },
  
  clearWorkflowState: (chatId) => set(state => {
    const newStates = { ...state.workflowStates };
    delete newStates[chatId];
    return { workflowStates: newStates };
  }),

  // Limpiar store
  clearStore: () => set({
    chats: [],
    activeChatId: null,
    messages: {},
    workflowStates: {},
    isLoading: false,
    error: null
  })
}));

export default useChatStore;