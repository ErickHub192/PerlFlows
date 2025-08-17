// src/hooks/useChatLogic.js

import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import { fetcher } from '../api/fetcher';
import useChatStore from '../stores/chatStore';
import { useErrorHandler } from './useErrorHandler';

export function useChatLogic(chatId) {
  // Store hooks
  const setActiveChat = useChatStore(s => s.setActiveChat);
  const chatHistory = useChatStore(s => s.chatHistories[chatId] || []);
  const fetchMessages = useChatStore(s => s.fetchMessages);
  const postMessage = useChatStore(s => s.sendMessage);

  // Error handling
  const { error, loading, withErrorHandler, clearError } = useErrorHandler();

  // 🚨 CRITICAL FIX: Race condition prevention
  const isInitializingRef = useRef(false);
  const currentChatIdRef = useRef(chatId);
  const mountedRef = useRef(true);

  // Update ref when chatId changes
  useEffect(() => {
    currentChatIdRef.current = chatId;
  }, [chatId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Initialize chat with race condition protection
  useEffect(() => {
    if (chatId && !isInitializingRef.current) {
      isInitializingRef.current = true;
      
      const initializeChat = async () => {
        try {
          // Only proceed if we're still mounted and chatId hasn't changed
          if (!mountedRef.current || currentChatIdRef.current !== chatId) {
            return;
          }
          
          setActiveChat(chatId);
          
          // Check if we already have messages for this chat
          const currentMessages = useChatStore.getState().chatHistories[chatId];
          if (!currentMessages || currentMessages.length === 0) {
            await fetchMessages(chatId);
          }
        } finally {
          isInitializingRef.current = false;
        }
      };

      initializeChat();
    }
  }, [chatId, setActiveChat, fetchMessages]);

  // Sanitize conversation helper
  const sanitizeConversation = useCallback((conv) =>
    conv
      .filter(m => !(m.role === 'assistant' && !m.content?.trim()))
      .map(m => ({ role: m.role, content: m.content }))
  , []);

  // 🚨 CRITICAL FIX: Race condition protection for sendMessage
  const sendingRef = useRef(false);

  // Send message to API with race condition protection
  const sendMessage = useCallback(
    withErrorHandler(async (userMessage) => {
      if (!userMessage.trim() || loading || sendingRef.current) {
        console.log('🚫 SendMessage blocked:', { 
          hasMessage: !!userMessage.trim(), 
          loading, 
          alreadySending: sendingRef.current 
        });
        return;
      }

      // Prevent multiple simultaneous sends
      sendingRef.current = true;

      try {
        // Verify we're still mounted and chatId is current
        if (!mountedRef.current || currentChatIdRef.current !== chatId) {
          console.log('🚫 SendMessage cancelled - component unmounted or chatId changed');
          return;
        }

        // Add user message to store immediately
        await postMessage(chatId, userMessage, 'user');
        
        // Get updated history
        const updatedHistory = [...chatHistory, { role: 'user', content: userMessage }];

        console.debug('[useChatLogic] Sending to /api/chat:', {
          session_id: chatId,
          message: userMessage,
          conversation: sanitizeConversation(updatedHistory),
        });

        // ✅ NUEVA LÓGICA: Manejar chats temporales
        const isTemporaryChat = chatId && chatId.startsWith('temp-');
        
        const response = await fetcher('/api/chat', {
          method: 'POST',
          body: {
            session_id: isTemporaryChat ? null : chatId, // null para chats temporales
            message: userMessage,
            conversation: sanitizeConversation(updatedHistory),
          },
        });

        // Check again if we're still mounted before processing response
        if (!mountedRef.current || currentChatIdRef.current !== chatId) {
          console.log('🚫 Response processing cancelled - component state changed');
          return;
        }

        // ✅ NUEVA LÓGICA: Actualizar store si se creó sesión automáticamente
        if (isTemporaryChat && response?.session_id) {
          // Importar el store para actualizar el chat temporal con el ID real
          const { getState, setState } = await import('../stores/chatStore.js');
          const store = getState();
          
          // Actualizar el chat temporal con el ID real del backend
          const tempHistory = store.chatHistories[chatId] || [];
          const newSession = {
            session_id: response.session_id,
            title: 'Nuevo chat',
            created_at: new Date().toISOString(),
          };
          
          setState((state) => ({
            chats: [...state.chats, newSession],
            activeChatId: response.session_id,
            chatHistories: {
              ...state.chatHistories,
              [response.session_id]: tempHistory,
            },
          }));
          
          // Actualizar el chatId local para futuras operaciones
          chatId = response.session_id;
        }

        // Handle response
        if (response?.assistant_response) {
          await postMessage(chatId, response.assistant_response, 'assistant');
        }

        return response;
      } finally {
        sendingRef.current = false;
      }
    }, { component: 'useChatLogic', action: 'sendMessage' }),
    [chatId, chatHistory, loading, postMessage, sanitizeConversation, withErrorHandler]
  );

  return {
    chatHistory,
    loading,
    error,
    sendMessage,
    clearError
  };
}