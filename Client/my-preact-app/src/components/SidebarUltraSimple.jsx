// src/components/SidebarUltraSimple.jsx
// Ultra simple sidebar - NO infinite loops, minimal re-renders

import { memo } from 'preact/compat';
import { useCallback, useEffect, useState, useRef } from 'preact/hooks';
import { Link } from 'preact-router/match';
import { route } from 'preact-router';
import useChatStore from '../stores/chatStore';

/**
 * Sidebar Ultra Simple: Solo muestra chats y permite crear nuevos
 * SIN bucles infinitos, SIN re-renders excesivos
 */
function SidebarUltraSimple() {
  // Store subscriptions - MINIMAL
  const chats = useChatStore(state => state.chats);
  const activeChatId = useChatStore(state => state.activeChatId);
  const addChat = useChatStore(state => state.addChat);
  const fetchSessions = useChatStore(state => state.fetchSessions);

  // Local state - MINIMAL
  const [isCreating, setIsCreating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const inititalizedRef = useRef(false);

  // Load chats ONCE on mount - NO dependencies to prevent loops
  useEffect(() => {
    if (inititalizedRef.current) return;
    
    const loadChats = async () => {
      try {
        await fetchSessions();
        inititalizedRef.current = true;
      } catch (err) {
        console.error('Error loading chats:', err);
      }
    };

    loadChats();
  }, [fetchSessions]); // Only fetchSessions dependency

  // Create new chat - simple and safe
  const handleNewChat = useCallback(async () => {
    if (isCreating) return;
    
    setIsCreating(true);
    
    try {
      const newId = await addChat();
      route(`/chat/${newId}`, true);
    } catch (err) {
      console.error('Error creating chat:', err);
      // Fallback
      const fallbackId = `chat-${Date.now()}`;
      route(`/chat/${fallbackId}`, true);
    } finally {
      setIsCreating(false);
    }
  }, [addChat, isCreating]);

  // Filter chats - simple
  const filteredChats = searchTerm 
    ? chats.filter(chat => 
        chat.title?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : chats;

  return (
    <div className="w-80 glass border-r border-primary text-text-primary flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-primary">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 surface-elevated rounded-xl flex items-center justify-center text-lg font-bold text-white">
            ⚡
          </div>
          <div className="text-lg font-bold gradient-text-elegant">QYRAL</div>
        </div>
        
        <button
          onClick={handleNewChat}
          disabled={isCreating}
          className="w-full btn-primary text-white px-4 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 focus-elegant mb-4 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="text-lg">{isCreating ? '⏳' : '+'}</span>
          {isCreating ? 'Creando...' : 'Nueva Automatización'}
        </button>
      </div>

      {/* Search */}
      <div className="p-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Buscar chats..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full surface-input rounded-xl px-4 py-3 pl-10 text-sm focus-elegant bg-transparent text-text-primary placeholder-text-muted"
          />
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-accent-muted">
            🔍
          </div>
        </div>
      </div>

      {/* Chat List - SIMPLE */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {filteredChats.length === 0 ? (
          <div className="text-center py-8 text-text-secondary">
            <div className="mb-4">✨ No hay chats aún</div>
            <div className="text-sm">Crea tu primer chat con el botón de arriba</div>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredChats.map(chat => {
              const isActive = chat.session_id === activeChatId;
              
              return (
                <Link
                  key={chat.session_id}
                  href={`/chat/${chat.session_id}`}
                  className={`block p-4 rounded-xl surface-elevated transition-all duration-200 hover:surface-card hover:transform hover:translate-x-1 ${
                    isActive ? 'surface-card border-accent bg-glass-medium' : ''
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-2 h-2 rounded-full bg-accent-muted"></div>
                    <div className="font-medium text-elegant text-sm line-clamp-1">
                      {chat.title || 'Chat sin título'}
                    </div>
                  </div>
                  <div className="text-xs text-subtle">
                    {new Date(chat.created_at || Date.now()).toLocaleDateString()}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// Export with display name for debugging
SidebarUltraSimple.displayName = 'SidebarUltraSimple';

export default memo(SidebarUltraSimple);