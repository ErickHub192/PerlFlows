import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { fetcher } from '../api/fetcher';

/**
 * Zustand store para gestionar sesiones de chat y sus mensajes.
 * - chats: lista de sesiones
 * - activeChatId: id de la sesión activa
 * - chatHistories: historial de mensajes por sesión
 * - fetchSessions: carga sesiones desde el servidor
 * - addChat: crea una sesión (título por defecto si viene vacío) y la activa
 * - removeChat, updateChat, setActiveChat
 * - fetchMessages, sendMessage, addMessage para manejar mensajes
 */
const useChatStore = create(
  persist(
    (set, get) => ({
      chats: [],
      activeChatId: null,
      chatHistories: {},
      // Intervalos no se persisten - se recrean cada sesión
      _intervals: null,
      get titleGenerationIntervals() {
        // Lazy initialization para evitar problemas de serialización
        if (!this._intervals || !(this._intervals instanceof Map)) {
          this._intervals = new Map();
        }
        return this._intervals;
      },

      /** Helper: Filter out system messages that shouldn't be displayed */
      filterSystemMessages: (messages) => {
        const filtered = (messages || []).filter(msg => {
          // ✅ DEBUG: Log each message being filtered
          console.log('🔍 FILTER CHECK:', {
            role: msg.role,
            content: (msg.content || '').substring(0, 50) + '...',
            isSelectionFeedback: msg.isSelectionFeedback,
            skipBackend: msg.skipBackend,
            hasContent: !!(msg.content && msg.content.trim())
          });
          
          // ✅ FIX: Always filter out system messages - they're for backend only
          if (msg.role === 'system') {
            console.log('🚫 FILTERED: System message');
            return false;
          }
          
          // ✅ FIX: Filter out selection feedback messages
          if (msg.isSelectionFeedback || msg.skipBackend) {
            console.log('🚫 FILTERED: Selection feedback or skipBackend');
            return false;
          }
          
          // ✅ FIX: Filter out empty assistant messages
          if (msg.role === 'assistant' && (!msg.content || !msg.content.trim())) {
            console.log('🚫 FILTERED: Empty assistant message');
            return false;
          }
          
          console.log('✅ PASSED: Message will be displayed');
          return true;
        });
        
        console.log('📝 UI FILTER: Filtered', messages?.length || 0, 'to', filtered.length, 'messages');
        return filtered;
      },

      /** Clean existing chat histories from system messages */
      cleanSystemMessages: () => {
        set((state) => {
          const cleanedHistories = {};
          Object.entries(state.chatHistories).forEach(([chatId, messages]) => {
            // Filter system messages and remove duplicates
            const filtered = get().filterSystemMessages(messages);
            const deduplicated = [];
            
            // Remove duplicates based on content + role
            filtered.forEach(msg => {
              const isDupe = deduplicated.some(existing =>
                existing.content === msg.content && existing.role === msg.role
              );
              if (!isDupe) {
                deduplicated.push(msg);
              }
            });
            
            cleanedHistories[chatId] = deduplicated;
          });
          
          console.log('🧹 Cleaned system messages and duplicates from existing chat histories');
          return {
            chatHistories: cleanedHistories,
          };
        });
      },

      /** Carga todas las sesiones de chat desde el servidor */
      fetchSessions: async () => {
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
          
          // ✅ FIX: Only update sessions, preserve chat histories to avoid losing loaded messages
          const currentState = get();
          set({
            chats: sessions || [],
            activeChatId: sessions && sessions.length ? (currentState.activeChatId || sessions[0].session_id) : null,
            // ✅ FIX: Preserve existing chat histories instead of resetting
            chatHistories: currentState.chatHistories, // Keep existing messages
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
              chatHistories: {},
            });
          }
          
          throw err;
        }
      },

      /**
       * Crea una nueva sesión en el servidor y la añade al store.
       * Si no se proporciona título, usa "Nuevo chat" y programa auto-generación.
       */
      addChat: async (title = '') => {
        try {
          console.log('Creating chat with title:', title);
          // Creamos la sesión en el backend con título temporal
          const session = await fetcher('/api/chats/', {
            method: 'POST',
            body: { title: title || 'Nuevo chat' },
          });
          console.log('Chat created successfully:', session);

          const newSession = {
            ...session,
            title: session.title || 'Nuevo chat',
          };

          set((state) => ({
            chats: [...state.chats, newSession],
            activeChatId: newSession.session_id,
            chatHistories: {
              ...state.chatHistories,
              [newSession.session_id]: [],
            },
          }));

          // Auto-title generation disabled - backend endpoint not available

          return newSession.session_id;
        } catch (err) {
          console.error('Error creating chat session:', err);
          // Instead of fallback ID, throw error to handle properly
          throw new Error('Failed to create chat session: ' + err.message);
        }
      },

      /**
       * Programa la auto-generación de título después de que haya suficientes mensajes
       */
      scheduleAutoTitleGeneration: (sessionId) => {
        // Limpiar intervalo anterior si existe
        const intervals = get().titleGenerationIntervals;
        const existingInterval = intervals && typeof intervals.get === 'function' ? intervals.get(sessionId) : null;
        if (existingInterval) {
          clearInterval(existingInterval);
        }

        const checkInterval = setInterval(async () => {
          try {
            // Verificar si la sesión está lista para generar título
            const readiness = await fetcher(`/api/chats/${sessionId}/title-ready`, {
              method: 'GET'
            });

            if (readiness.success && readiness.ready) {
              // Generar título automáticamente
              const result = await get().generateTitleForSession(sessionId);
              
              if (result.success) {
                console.log(`Auto-generated title for session ${sessionId}: "${result.title}"`);
              }
              
              // Limpiar el intervalo una vez que se genere o falle
              clearInterval(checkInterval);
              const intervals = get().titleGenerationIntervals;
              if (intervals && typeof intervals.delete === 'function') {
                intervals.delete(sessionId);
              }
            }
          } catch (err) {
            console.error('Error checking title readiness:', err);
            // Limpiar el intervalo si hay error
            clearInterval(checkInterval);
            const intervals = get().titleGenerationIntervals;
            if (intervals && typeof intervals.delete === 'function') {
              intervals.delete(sessionId);
            }
          }
        }, 10000); // Cambiar a 10 segundos en lugar de 3

        // Guardar referencia
        const intervalsMap = get().titleGenerationIntervals;
        if (intervalsMap && typeof intervalsMap.set === 'function') {
          intervalsMap.set(sessionId, checkInterval);
        }
        
        // Limpiar después de 30 segundos en lugar de 2 minutos
        setTimeout(() => {
          clearInterval(checkInterval);
          const timeoutIntervalsMap = get().titleGenerationIntervals;
          if (timeoutIntervalsMap && typeof timeoutIntervalsMap.delete === 'function') {
            timeoutIntervalsMap.delete(sessionId);
          }
        }, 30000);
      },

      /**
       * Genera título para una sesión específica
       */
      generateTitleForSession: async (sessionId, forceRegenerate = false) => {
        try {
          const result = await fetcher(`/api/chats/${sessionId}/generate-title?force_regenerate=${forceRegenerate}`, {
            method: 'PATCH'
          });

          if (result.success) {
            // Actualizar el título en el store
            set((state) => ({
              chats: state.chats.map((chat) =>
                chat.session_id === sessionId 
                  ? { ...chat, title: result.title }
                  : chat
              )
            }));

            return result;
          } else {
            console.error('Failed to generate title:', result.message);
            return result;
          }
        } catch (err) {
          console.error('Error generating title for session:', err);
          return {
            success: false,
            message: err.message || 'Error generating title'
          };
        }
      },

      /**
       * Verifica si una sesión está lista para generar título
       */
      checkTitleReadiness: async (sessionId) => {
        try {
          const result = await fetcher(`/api/chats/${sessionId}/title-ready`, {
            method: 'GET'
          });
          return result;
        } catch (err) {
          console.error('Error checking title readiness:', err);
          return {
            success: false,
            ready: false,
            message: err.message || 'Error checking readiness'
          };
        }
      },

      /** Cambia la sesión activa */
      setActiveChat: (id) => set({ activeChatId: id }),

      /** Actualiza título u otros campos de una sesión localmente */
      updateChat: (id, updates) =>
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.session_id === id ? { ...chat, ...updates } : chat
          ),
        })),

      /** Elimina la sesión en el servidor y en el store */
      removeChat: async (id) => {
        // Optimistic UI update - remove from UI immediately
        const currentState = get();
        const chatExists = currentState.chats.some(chat => chat.session_id === id);
        
        if (!chatExists) {
          console.log('Chat already removed from UI:', id);
          return; // Chat doesn't exist in UI, nothing to do
        }

        // Immediately update UI for better user experience
        const wasActiveChat = currentState.activeChatId === id;
        
        set((state) => ({
          chats: state.chats.filter((chat) => chat.session_id !== id),
          activeChatId: state.activeChatId === id ? null : state.activeChatId,
          chatHistories: Object.fromEntries(
            Object.entries(state.chatHistories).filter(([chatId]) => chatId !== id)
          ),
        }));

        // ✅ NAVEGACIÓN AUTOMÁTICA: Siempre redirigir a nuevo chat si eliminamos el chat activo
        if (wasActiveChat) {
          // Importar route de manera dinámica para evitar problemas de dependencias circulares
          const { route } = await import('preact-router');
          route('/chat', true);
        }
        
        // Clean up auto-generation intervals immediately
        const intervals = get().titleGenerationIntervals;
        if (intervals && typeof intervals.has === 'function' && intervals.has(id)) {
          clearInterval(intervals.get(id));
          intervals.delete(id);
        }

        try {
          // Make API call after UI update for optimistic UX
          console.log(`🗑️ Attempting to delete chat ${id} from server...`);
          console.log(`📡 DELETE request to: /api/chats/${id}`);
          
          const response = await fetcher(`/api/chats/${id}`, { method: 'DELETE' });
          console.log('✅ Chat deleted successfully from server:', id);
          console.log('📊 Server response:', response);
          
          // ✅ FORCE SYNC: Refetch from server to ensure consistency 
          // This prevents the localStorage cache from having stale data
          setTimeout(() => {
            get().fetchSessions().catch(console.error);
          }, 100);
          
          return response;
        } catch (err) {
          console.error('❌ Error deleting chat session from server:', err);
          console.error('❌ Full error details:', {
            status: err?.status,
            message: err?.message,
            detail: err?.detail,
            url: `/api/chats/${id}`,
            method: 'DELETE'
          });
          
          // Restore chat in UI if server deletion failed (pessimistic rollback)
          if (err?.status !== 404) {
            // Only restore if it wasn't a "not found" error
            const chatToRestore = currentState.chats.find(chat => chat.session_id === id);
            if (chatToRestore) {
              set((state) => ({
                chats: [...state.chats, chatToRestore].sort((a, b) => 
                  new Date(b.created_at) - new Date(a.created_at)
                ),
                activeChatId: currentState.activeChatId === id ? id : state.activeChatId,
              }));
              console.log('Restored chat in UI due to server error:', id);
            }
          }
          
          throw err; // Re-throw to allow component-level error handling
        }
      },

      /** Añade un mensaje al historial local */
      addMessage: (chatId, message) => {
        // ✅ FIX: Skip backend for UI-only messages
        if (message.skipBackend || message.isSelectionFeedback) {
          console.log('💫 UI-only message, skipping backend processing:', message.content?.substring(0, 50));
          // Continue with UI addition only
        }
        
        // ✅ FIX: Filter out system messages that shouldn't be displayed to users
        const filteredMessages = get().filterSystemMessages([message]);
        if (filteredMessages.length === 0) {
          console.log('🚫 Filtering out system message:', (message.content || '').substring(0, 50) + '...');
          return; // Don't add to UI
        }
        
        set((state) => {
          const prev = state.chatHistories[chatId] || [];
          
          // Simple duplicate check - only exact matches
          const isDuplicate = prev.some(existingMsg => 
            existingMsg.content === message.content && 
            existingMsg.role === message.role &&
            existingMsg.timestamp === message.timestamp
          );
          
          if (isDuplicate) {
            console.log('🚫 Preventing exact duplicate message');
            return state;
          }
          
          console.log('✅ UI ADD: Adding new message to store:', {
            chatId,
            role: message.role,
            content: (message.content || '').substring(0, 50) + '...',
            timestamp: message.timestamp,
            hasData: !!message.data,
            smartForm: !!(message.smart_form || (message.data && JSON.parse(message.data || '{}').smart_form))
          });
          
          return {
            chatHistories: {
              ...state.chatHistories,
              [chatId]: [...prev, message],
            },
          };
        });
      },

      /** Agrega mensaje de asistente con datos estructurados para botones */
      addAssistantMessage: (chatId, content, messageData = null) => {
        const assistantMessage = {
          role: 'assistant',
          content: content,
          timestamp: new Date().toISOString(),
          // 🔧 FIX: Include structured data for button states
          data: messageData ? JSON.stringify(messageData) : null,
          // Keep backwards compatibility
          ...messageData
        };
        
        get().addMessage(chatId, assistantMessage);
        console.log('🔧 FIX: Added assistant message with data:', { content, messageData });
      },

      /** Carga todos los mensajes de una sesión desde el servidor */
      fetchMessages: async (chatId) => {
        try {
          // ✅ FIX: Check if messages are already loaded to avoid unnecessary fetches
          const currentMessages = get().chatHistories[chatId];
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
          
          // ✅ FIX: Filter out system messages that shouldn't be displayed to users
          const filteredMessages = get().filterSystemMessages(messages);
          
          // ✅ FIX: Remove duplicates from server response
          const deduplicatedMessages = [];
          filteredMessages.forEach(msg => {
            const isDupe = deduplicatedMessages.some(existing =>
              existing.content === msg.content && 
              existing.role === msg.role &&
              existing.timestamp === msg.timestamp
            );
            if (!isDupe) {
              deduplicatedMessages.push(msg);
            }
          });
          
          console.log('✅ Fetched messages for chat:', chatId, '- total:', messages?.length || 0, '- filtered:', filteredMessages.length, '- deduplicated:', deduplicatedMessages.length);
          
          set((state) => ({
            chatHistories: {
              ...state.chatHistories,
              [chatId]: deduplicatedMessages,
            },
          }));
          
          return messages;
        } catch (err) {
          console.error('❌ Error fetching messages for', chatId, err);
          
          // ✅ FIX: Only set empty array if there are NO existing messages (preserve existing messages on error)
          const existingMessages = get().chatHistories[chatId];
          if (!existingMessages || existingMessages.length === 0) {
            console.log('📝 Setting empty array for chat:', chatId, '(no existing messages)');
            set((state) => ({
              chatHistories: {
                ...state.chatHistories,
                [chatId]: [],
              },
            }));
          } else {
            console.log('💾 Preserving existing messages for chat:', chatId, '- count:', existingMessages.length);
          }
          
          throw err;
        }
      },

      /** Envía un mensaje y lo persiste en el servidor */
      sendMessage: async (chatId, role, content, messageData = null) => {
        try {
          console.log('🏪 Store sendMessage called:', { chatId, role, content, messageData });
          
          // Add user message to UI immediately
          const userMessage = {
            role: 'user',
            content: content,
            timestamp: new Date().toISOString(),
            status: 'sending'
          };
          get().addMessage(chatId, userMessage);
          
          // Get workflow type from mode store
          const { default: useModeStore } = await import('../stores/modeStore');
          const currentMode = useModeStore.getState().mode;
          const workflowType = currentMode === 'ai' ? 'agent' : 'classic';
          
          console.log('🔧 Using workflow type:', workflowType, 'from mode:', currentMode);
          
          // ✅ FIX: Add timeout and retry logic for better persistence
          let response;
          let retryCount = 0;
          const maxRetries = 2;
          const timeout = 15000; // 15 seconds timeout
          
          while (retryCount <= maxRetries) {
            try {
              const controller = new AbortController();
              const timeoutId = setTimeout(() => controller.abort(), timeout);
              
              response = await fetcher(
                `/api/chat`,
                {
                  method: 'POST',
                  body: { 
                    session_id: chatId,
                    message: content,
                    conversation: get().chatHistories[chatId] || [],
                    workflow_type: workflowType
                  },
                  signal: controller.signal
                }
              );
              
              clearTimeout(timeoutId);
              
              // ✅ FIX: Update user message status to sent
              set((state) => {
                const messages = state.chatHistories[chatId] || [];
                const updatedMessages = messages.map(msg => 
                  msg.content === content && msg.role === 'user' && msg.status === 'sending' 
                    ? { ...msg, status: 'sent' }
                    : msg
                );
                return {
                  chatHistories: {
                    ...state.chatHistories,
                    [chatId]: updatedMessages
                  }
                };
              });
              
              break; // Success, exit retry loop
              
            } catch (error) {
              clearTimeout && clearTimeout();
              retryCount++;
              
              if (retryCount > maxRetries) {
                // ✅ FIX: Mark message as failed but keep it visible
                console.error('❌ Failed to send message after retries:', error);
                set((state) => {
                  const messages = state.chatHistories[chatId] || [];
                  const updatedMessages = messages.map(msg => 
                    msg.content === content && msg.role === 'user' && msg.status === 'sending'
                      ? { ...msg, status: 'failed', error: error.message }
                      : msg
                  );
                  return {
                    chatHistories: {
                      ...state.chatHistories,
                      [chatId]: updatedMessages
                    }
                  };
                });
                throw error;
              }
              
              console.warn(`⚠️ Retry ${retryCount}/${maxRetries} for message:`, error.message);
              await new Promise(resolve => setTimeout(resolve, 1000 * retryCount)); // Exponential backoff
            }
          }
          
          // ✅ FIX: Process response outside retry loop but inside try block
          console.log('✅ Server response received:', response);
          console.log('🔍 Checking for service selection triggers:', {
            similar_services_found: response.similar_services_found,
            service_groups: response.service_groups,
            service_suggestions: response.service_suggestions,
            clarify: response.clarify
          });
          
          // 🔍 DEEP DEBUG: Log entire response object structure
          console.log('🔍 COMPLETE RESPONSE OBJECT:');
          console.log(response);
          console.log('🔍 RESPONSE KEYS:', Object.keys(response));
          
          // 🔍 Check specifically for the properties we need
          console.log('🔍 PROPERTY CHECK:');
          console.log('- hasOwnProperty similar_services_found:', response.hasOwnProperty('similar_services_found'));
          console.log('- hasOwnProperty service_groups:', response.hasOwnProperty('service_groups'));
          console.log('- hasOwnProperty smart_forms_required:', response.hasOwnProperty('smart_forms_required'));
          console.log('- hasOwnProperty smart_form:', response.hasOwnProperty('smart_form'));
          console.log('- smart_forms_required value:', response.smart_forms_required);
          console.log('- smart_form value:', response.smart_form);
          
          // ✅ Check for service selection triggers BEFORE adding message
          if (response.similar_services_found && response.service_groups?.length) {
            console.log('🎯 Triggering service selection dropdown');
            // Store service selection data globally so ChatView can access it
            window.pendingServiceSelection = {
              chatId: chatId,
              serviceGroups: response.service_groups,
              originalMessage: response.reply
            };
          }
          
          // ✅ Add assistant response if successful
          if (response.reply && response.status !== 'error') {
            console.log('🔍 CHATSTORE: Processing response with oauth_requirements:', response.oauth_requirements);
            console.log('🔍 CHATSTORE: Full response object:', response);
            console.log('🔍 CHATSTORE: SmartForm data:', {
              smart_forms_required: response.smart_forms_required,
              smart_form: response.smart_form,
              hasSmartForm: !!(response.smart_form && response.smart_form.fields)
            });
            
            const assistantMessage = {
              role: 'assistant', 
              content: response.reply,
              timestamp: new Date().toISOString(),
              // 🔧 FIX: Include workflow status and metadata for button states
              data: JSON.stringify({
                status: response.status,
                workflow_status: response.workflow_status,
                workflow_action: response.workflow_action,
                metadata: response.metadata,
                steps: response.steps || [],
                oauth_requirements: response.oauth_requirements || [],
                finalize: response.finalize || false,
                editable: response.editable || false,
                enhanced_workflow: response.enhanced_workflow || false,
                similar_services_found: response.similar_services_found || false,
                service_groups: response.service_groups || null,
                service_suggestions: response.service_suggestions || null,
                smart_forms_required: response.smart_forms_required || false,
                smart_form: response.smart_form || null
              }),
              // ✨ Keep backwards compatibility
              oauth_requirements: response.oauth_requirements || [],
              steps: response.steps || [],
              finalize: response.finalize || false,
              editable: response.editable || false,
              enhanced_workflow: response.enhanced_workflow || false,
              similar_services_found: response.similar_services_found || false,
              service_groups: response.service_groups || null,
              service_suggestions: response.service_suggestions || null,
              smart_forms_required: response.smart_forms_required || false,
              smart_form: response.smart_form || null
            };
            
            console.log('📨 CHATSTORE: About to add assistant message:', {
              content: assistantMessage.content.substring(0, 100) + '...',
              hasSmartForm: assistantMessage.smart_forms_required,
              smartFormFields: assistantMessage.smart_form?.fields?.length || 0
            });
            
            get().addMessage(chatId, assistantMessage);
            
            // ✨ Check for smart forms and set up context for ChatView
            console.log('🔍 CHATSTORE: Checking for smart forms...', {
              smart_forms_required: response.smart_forms_required,
              has_smart_form: !!response.smart_form,
              smart_form_title: response.smart_form?.title,
              smart_form_fields: response.smart_form?.fields?.length || 0
            });
            
            if (response.smart_forms_required && response.smart_form) {
              console.log('🎉 CHATSTORE: Smart form detected! Setting up context:', {
                title: response.smart_form.title,
                fields: response.smart_form.fields?.length || 0,
                sections: response.smart_form.sections?.length || 0
              });
              
              window.smartFormContext = {
                formSchema: response.smart_form,
                isSmartForm: true,
                backendData: response
              };
              
              // Trigger smart form display - signal to ChatView that smart form is ready
              console.log('🚀 CHATSTORE: Dispatching smartFormReady event');
              window.dispatchEvent(new CustomEvent('smartFormReady', { 
                detail: { 
                  chatId, 
                  smartForm: response.smart_form,
                  backendData: response
                } 
              }));
            } else {
              console.log('⚠️ CHATSTORE: No smart forms detected - requirements:', response.smart_forms_required, 'form:', !!response.smart_form);
            }
          } else if (response.status === 'error') {
            console.warn('⚠️ Server returned error status');
            const errorMessage = {
              role: 'assistant', 
              content: 'Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo.',
              timestamp: new Date().toISOString()
            };
            get().addMessage(chatId, errorMessage);
          }
          
          return { success: true };
        } catch (err) {
          console.error('Error sending message to', chatId, err);
          // TODO: Podrías quitar el mensaje del usuario si falla, pero por ahora lo dejamos
          throw err;
        }
      },

      /** Envía mensaje con servicios seleccionados - evita duplicación */
      sendMessageWithServices: async (chatId, message, selectedServices, workflowType = 'classic') => {
        try {
          console.debug('[Store] Sending message with services:', { chatId, selectedServices });
          
          // NO agregar mensaje del usuario otra vez - ya está en el chat
          
          // Llamar al endpoint específico
          const response = await fetcher('/api/chat/with-services', {
            method: 'POST',
            body: {
              session_id: chatId,
              message,
              conversation: get().chatHistories[chatId] || [],
              workflow_type: workflowType,
              selected_services: selectedServices
            },
          });

          // Procesar respuesta de manera consistente
          if (response.reply && response.status !== 'error') {
            console.log('🔍 CHATSTORE WITH-SERVICES: Processing response with oauth_requirements:', response.oauth_requirements);
            const assistantMessage = {
              role: 'assistant',
              content: response.reply,
              timestamp: new Date().toISOString(),
              // ✨ Include ALL response fields for ChatView access
              oauth_requirements: response.oauth_requirements || [],
              steps: response.steps || [],
              finalize: response.finalize || false,
              editable: response.editable || false,
              enhanced_workflow: response.enhanced_workflow || false,
              similar_services_found: response.similar_services_found || false,
              service_groups: response.service_groups || null,
              service_suggestions: response.service_suggestions || null,
              // ✨ Include smart form fields for processing
              smart_forms_required: response.smart_forms_required || false,
              smart_form: response.smart_form || null
            };
            get().addMessage(chatId, assistantMessage);
            
            // ✨ Check for smart forms and set up context for ChatView
            if (response.smart_forms_required && response.smart_form) {
              console.log('🔍 CHATSTORE WITH-SERVICES: Smart form detected, setting up context:', response.smart_form);
              window.smartFormContext = {
                formSchema: response.smart_form,
                isSmartForm: true,
                backendData: response
              };
              
              // Trigger smart form display - signal to ChatView that smart form is ready
              window.dispatchEvent(new CustomEvent('smartFormReady', { 
                detail: { 
                  chatId, 
                  smartForm: response.smart_form,
                  backendData: response
                } 
              }));
            }
          }

          // Manejar casos especiales (nodos, finalización, etc.)
          return response;
          
        } catch (err) {
          console.error('[Store] Error sending message with services:', err);
          throw err;
        }
      },

      /** Elimina una conversación */
      deleteChat: (chatId) => {
        set((state) => ({
          chats: state.chats.filter(chat => chat.session_id !== chatId),
          chatHistories: Object.fromEntries(
            Object.entries(state.chatHistories).filter(([id]) => id !== chatId)
          ),
          activeChatId: state.activeChatId === chatId ? null : state.activeChatId,
        }));
        
        // Limpiar auto-generación de título si existe
        const intervals = get().titleGenerationIntervals;
        if (intervals && typeof intervals.has === 'function' && intervals.has(chatId)) {
          clearInterval(intervals.get(chatId));
          intervals.delete(chatId);
        }
      },

      /** Actualiza información de una conversación */
      updateChat: (chatId, updateData) => {
        set((state) => ({
          chats: state.chats.map(chat => 
            chat.session_id === chatId 
              ? { ...chat, ...updateData }
              : chat
          ),
        }));
      },


      /** EMERGENCY: Force complete reset (for debugging - keep commented for future use) */
      // forceReset: () => {
      //   console.log('🚨 FORCE RESET: Clearing all chat data');
      //   localStorage.removeItem('chat-store');
      //   set({
      //     chats: [],
      //     activeChatId: null,
      //     chatHistories: {},
      //   });
      //   // Force page reload to ensure clean state
      //   window.location.reload();
      // },
    }),
    {
      name: 'chat-store', // clave en localStorage
      partialize: (state) => {
        // Excluir intervalos de la persistencia
        const { _intervals, ...persistedState } = state;
        return persistedState;
      },
      // ✅ Add versioning to force refresh when needed  
      version: 3, // ✅ Increment version again for aggressive cleanup
      migrate: (persistedState, version) => {
        // Force complete reset to eliminate all duplicates
        console.log('🔄 Store version upgraded to v3 - COMPLETE RESET to eliminate duplicates');
        
        return {
          chats: [],
          activeChatId: null,
          chatHistories: {},
          _migrated: true,
          _resetDone: true
        };
      },
    }
  )
);

export default useChatStore;
