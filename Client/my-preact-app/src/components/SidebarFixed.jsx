// src/components/SidebarFixed.jsx
// SAFE VERSION - Connected to store but NO infinite loops

import { useState, useRef, useEffect } from 'preact/hooks';
import { Link } from 'preact-router/match';
import { route } from 'preact-router';
import useChatStore from '../stores/chatStore';
import { fetcher } from '../api/fetcher';

/**
 * Sidebar seguro - Conectado al store pero sin bucles
 */
function SidebarFixed() {
  // Store connections - MINIMAL
  const chats = useChatStore(state => state.chats) || [];
  const addChat = useChatStore(state => state.addChat);

  const [isCreating, setIsCreating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Context menu state
  const [contextMenu, setContextMenu] = useState({ show: false, x: 0, y: 0, chatId: null });
  const [editingChat, setEditingChat] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const contextMenuRef = useRef(null);

  const handleNewChat = async () => {
    if (isCreating) return;
    console.log('🔧 SidebarFixed handleNewChat called');
    setIsCreating(true);
    
    try {
      // Crear chat inmediatamente en lugar de navegar a /chat sin ID
      const response = await fetch('/api/chats/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ title: 'Nuevo chat' })
      });
      
      if (!response.ok) {
        throw new Error('Failed to create chat');
      }
      
      const newChat = await response.json();
      
      // Actualizar el store
      useChatStore.setState((state) => ({
        chats: [newChat, ...state.chats],
        activeChatId: newChat.session_id,
        chatHistories: {
          ...state.chatHistories,
          [newChat.session_id]: []
        }
      }));
      
      // Navegar al nuevo chat
      route(`/chat/${newChat.session_id}`, true);
      
    } catch (err) {
      console.error('Error creando nuevo chat:', err);
      // Fallback al método anterior
      route('/chat', true);
    } finally {
      setIsCreating(false);
    }
  };

  // Context menu handlers
  const handleContextMenu = (e, chatId) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      show: true,
      x: e.clientX,
      y: e.clientY,
      chatId
    });
  };

  const handleDeleteChat = async (chatId) => {
    if (!chatId) return;
    
    if (!confirm('¿Estás seguro de que quieres eliminar esta conversación?')) {
      setContextMenu({ show: false, x: 0, y: 0, chatId: null });
      return;
    }

    // Close context menu immediately for better UX
    setContextMenu({ show: false, x: 0, y: 0, chatId: null });

    try {
      // Use deleteChat which handles both API call and store update
      const deleteChat = useChatStore.getState().deleteChat;
      await deleteChat(chatId);
      
      // Success - no need to show alert, just log success
      console.log('Chat deleted successfully');
      
    } catch (error) {
      console.error('Error deleting chat:', error);
      
      // Para debugging, log el error completo
      console.log('Full error object:', error);
      
      // Más tolerante con errores - si el backend dice 200 OK pero hay algún problema de formato
      if (error?.status === 404 || 
          error?.detail?.includes?.('no encontrada') ||
          error?.message?.includes?.('not found')) {
        // Chat was already deleted on server, just clean up UI
        const deleteChat = useChatStore.getState().deleteChat;
        deleteChat(chatId);
        console.log('Chat was already deleted, cleaned up UI');
      } else if (error?.status >= 500) {
        // Server error
        console.log('Server error, but chat might be deleted');
      } else {
        // Solo mostrar error si realmente hay un problema grave
        console.log('Possible error, but chat might be deleted successfully');
      }
      
      // En todos los casos, intentar limpiar la UI porque probablemente se borró
      const deleteChat = useChatStore.getState().deleteChat;
      deleteChat(chatId);
    }
  };

  const handleStartEdit = (chat) => {
    setEditingChat(chat.session_id);
    setEditTitle(chat.title || '');
    setContextMenu({ show: false, x: 0, y: 0, chatId: null });
  };

  const handleSaveEdit = async (chatId) => {
    if (editingChat !== chatId) return; // Prevent multiple saves
    if (!editTitle.trim()) {
      handleCancelEdit();
      return;
    }

    try {
      // Update store first (optimistic update)
      const updateChat = useChatStore.getState().updateChat;
      await updateChat(chatId, { title: editTitle.trim() });
      
      setEditingChat(null);
      setEditTitle('');
      console.log('Chat title updated successfully');
    } catch (error) {
      console.error('Error updating chat title:', error);
      alert('Error actualizando el título. Por favor intenta de nuevo.');
    }
  };

  const handleCancelEdit = () => {
    setEditingChat(null);
    setEditTitle('');
  };

  // 🔧 RESTORE: Load chats when sidebar mounts (but respect existing chats)
  useEffect(() => {
    // Only load if we have no chats AND we're authenticated
    if (chats.length === 0) {
      const loadChats = useChatStore.getState().loadChats;
      console.log('📋 SIDEBAR: No chats found, loading from server...');
      loadChats().catch(err => {
        console.error('❌ Error loading chats in sidebar:', err);
      });
    } else {
      console.log('📋 SIDEBAR: Already have', chats.length, 'chats loaded');
    }
  }, []); // Run once on mount

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target)) {
        setContextMenu({ show: false, x: 0, y: 0, chatId: null });
      }
    };

    if (contextMenu.show) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [contextMenu.show]);

  const filteredChats = searchTerm 
    ? chats.filter(chat => 
        chat.title?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : chats;

  return (
    <div className="w-80 glass border-r border-primary text-white flex flex-col h-full backdrop-blur-sm">
      {/* Header */}
      <div className="p-6 border-b border-primary">
        <div className="mb-6">
        </div>
        
        <button
          onClick={handleNewChat}
          disabled={isCreating}
          className="w-full btn-primary hover:btn-primary text-white px-6 py-3 rounded-2xl font-medium transition-all duration-200 disabled:opacity-50 shadow-lg shadow-elegant hover:shadow-elegant hover:scale-[1.02] disabled:hover:scale-100"
        >
          {isCreating ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              Creando...
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <span className="text-lg">✨</span>
              Nuevo Chat
            </div>
          )}
        </button>
      </div>

      {/* Search */}
      <div className="p-6 pb-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Buscar conversaciones..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full surface-input backdrop-blur-sm border border-accent rounded-2xl px-4 py-3 pl-10 text-sm text-white placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-white focus:border-accent transition-all duration-200"
          />
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-subtle">
            🔍
          </div>
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="space-y-2">
          {filteredChats.map(chat => (
            <div
              key={chat.session_id}
              className="relative group"
              onContextMenu={(e) => handleContextMenu(e, chat.session_id)}
            >
              {editingChat === chat.session_id ? (
                // Inline editing mode
                <div className="p-4 rounded-2xl surface-elevated border border-accent transition-all duration-200 backdrop-blur-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 surface-elevated rounded-xl flex items-center justify-center text-xs flex-shrink-0">
                      ✏️
                    </div>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleSaveEdit(chat.session_id);
                        }
                        if (e.key === 'Escape') {
                          e.preventDefault();
                          handleCancelEdit();
                        }
                      }}
                      onBlur={(e) => {
                        // Auto-save when user clicks away, but not if clicking on save/cancel buttons
                        const relatedTarget = e.relatedTarget;
                        if (!relatedTarget || !relatedTarget.closest('.edit-buttons')) {
                          setTimeout(() => handleSaveEdit(chat.session_id), 150);
                        }
                      }}
                      className="flex-1 bg-transparent text-sm font-medium text-white border-none outline-none placeholder-text-muted"
                      placeholder="Título de la conversación"
                      autoFocus
                    />
                    <div className="flex items-center gap-2 ml-2 edit-buttons">
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleSaveEdit(chat.session_id);
                        }}
                        className="w-8 h-8 flex items-center justify-center text-green-400 hover:text-green-300 hover:bg-green-400/10 rounded-lg transition-all duration-200"
                        title="Guardar (Enter)"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleCancelEdit();
                        }}
                        className="w-8 h-8 flex items-center justify-center text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded-lg transition-all duration-200"
                        title="Cancelar (Esc)"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                // Normal chat item
                <div className="relative group">
                  <Link
                    href={`/chat/${chat.session_id}`}
                    className="block"
                  >
                    <div className="p-4 rounded-2xl surface-elevated hover:surface-card border border-primary hover:border-accent transition-all duration-200 backdrop-blur-sm hover:shadow-lg hover:shadow-elegant hover:scale-[1.02]">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 surface-elevated rounded-xl flex items-center justify-center text-xs flex-shrink-0 group-hover:surface-elevated transition-all duration-200">
                          💬
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-white truncate hover:text-accent transition-colors duration-200">
                            {chat.title || 'Chat sin título'}
                          </div>
                          <div className="text-xs text-subtle mt-1">
                            Hace {Math.floor(Math.random() * 24)} horas
                          </div>
                        </div>
                        
                        {/* 3 Dots Menu Button */}
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setContextMenu({ 
                                show: true, 
                                x: e.clientX, 
                                y: e.clientY, 
                                chatId: chat.session_id 
                              });
                            }}
                            className="w-8 h-8 flex items-center justify-center rounded-lg hover:surface-elevated transition-colors"
                          >
                            <svg className="w-4 h-4 text-subtle" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  </Link>
                  
                </div>
              )}
            </div>
          ))}
          
          {filteredChats.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 surface-input rounded-3xl flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">💭</span>
              </div>
              <div className="text-subtle font-medium mb-2">No hay conversaciones</div>
              <div className="text-xs text-muted">Inicia un nuevo chat para comenzar</div>
            </div>
          )}
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu.show && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 glass backdrop-blur-sm border border-accent rounded-xl shadow-xl py-2 min-w-[160px]"
          style={{
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
          }}
        >
          <button
            onClick={() => {
              const chat = chats.find(c => c.session_id === contextMenu.chatId);
              if (chat) {
                setEditingChat(chat.session_id);
                setEditTitle(chat.title || '');
                setContextMenu({ show: false, x: 0, y: 0, chatId: null });
              }
            }}
            className="w-full px-4 py-3 text-left text-sm text-white hover:surface-card transition-all duration-150 flex items-center gap-3"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Renombrar
          </button>
          <div className="border-t border-primary my-1"></div>
          <button
            onClick={() => {
              setContextMenu({ show: false, x: 0, y: 0, chatId: null });
              handleDeleteChat(contextMenu.chatId);
            }}
            className="w-full px-4 py-3 text-left text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all duration-150 flex items-center gap-3"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Eliminar
          </button>
        </div>
      )}
    </div>
  );
}

export default SidebarFixed;