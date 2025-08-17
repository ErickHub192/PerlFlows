// src/App.jsx
import { useState, useEffect } from 'preact/hooks';
import { Router, route } from 'preact-router';
import { Link } from 'preact-router/match';
import SidebarFixed from './components/SidebarFixed';
import LoginForm from './components/LoginForm';
import CredentialsManager from './components/CredentialsManager';
import DeployAgentModal from './components/DeployAgentModal';
import ModelSelector from './components/ModelSelector';
import useChatStore from './stores/chatStore';
import useModeStore from './stores/modeStore';
import Dashboard from './pages/Dashboard';
import ChatView from './pages/ChatView';
import ExecutionsList from './pages/ExecutionsList';
import ExecutionDetail from './pages/ExecutionDetail';
import MarketplacePage from './pages/MarketplacePage';
import WorkflowsPage from './pages/WorkflowsPage';
import AgentsPage from './pages/AgentsPage';
import AgentDetail from './pages/AgentDetail';
import OAuthCallback from './pages/OAuthCallback';
import { useAuth } from './hooks/useAuth';
import Notifications from './components/Notifications';
import ErrorBoundary from './components/ErrorBoundary';
import { setupTokenAutoRefresh } from './utils/tokenRefresh';

function App() {
  const [isHydrated, setIsHydrated] = useState(false);
  const { chats, activeChatId, addChat } = useChatStore();
  const { token, subscribeToLogout } = useAuth();
  const { mode } = useModeStore();                       // único origen de la verdad
  const [showCredModal, setShowCredModal] = useState(false);
  const [showDeployModal, setShowDeployModal] = useState(false);

  const isAuthenticated = !!token;

  // 🔧 Evitar errores de hidratación y configurar refresh automático
  useEffect(() => {
    setIsHydrated(true);
    
    // Configurar refresh automático de tokens al cargar la app
    if (token) {
      setupTokenAutoRefresh();
    }
  }, [token]);

  /* 1️⃣ Cargar sesiones solo cuando sea necesario (no automáticamente) */
  // Removed automatic fetchSessions on authentication

  /* 2️⃣ Redirigir al login en logout */
  useEffect(() => {
    const unsubscribe = subscribeToLogout(() => {
      route('/', true);
    });
    return unsubscribe;
  }, [subscribeToLogout]);

  /* 3️⃣ Si no hay token, mostrar dashboard con funciones limitadas */
  const [showLoginModal, setShowLoginModal] = useState(false);

  // SOLUCION SIMPLE: Sidebar solo en chat, sin polling demoníaco
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  
  // Track path changes
  useEffect(() => {
    const handleRouteChange = () => {
      setCurrentPath(window.location.pathname);
    };
    
    // Listen to both popstate and pushstate/replacestate
    window.addEventListener('popstate', handleRouteChange);
    
    // Override pushState and replaceState to capture programmatic navigation
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    
    history.pushState = function(...args) {
      originalPushState.apply(this, args);
      handleRouteChange();
    };
    
    history.replaceState = function(...args) {
      originalReplaceState.apply(this, args);
      handleRouteChange();
    };
    
    return () => {
      window.removeEventListener('popstate', handleRouteChange);
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
    };
  }, []);
  
  const showSidebar = (currentPath.startsWith('/chat') && isAuthenticated);

  // 🔧 Evitar renderizar antes de la hidratación
  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-gradient-main flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 surface-elevated rounded-3xl flex items-center justify-center mx-auto mb-4 shadow-elegant">
            <img 
              src="/logo.svg" 
              alt="QYRAL Logo" 
              className="w-10 h-10"
              style={{ filter: 'none' }}
            />
          </div>
          <div className="text-lg font-semibold gradient-text">Cargando QYRAL AI...</div>
        </div>
      </div>
    );
  }

  /* 4️⃣ Render normal */
  return (
    <div className="min-h-screen flex bg-gradient-main text-text-primary">
      {showSidebar && isAuthenticated && (
        <SidebarFixed />
      )}

      <div className="flex-1 flex flex-col">
        {!showSidebar && (
          <div className="p-4 border-b border-primary glass">
            {/* Navigation Header */}
            <div className="flex flex-wrap gap-2 items-center justify-between">
              <div className="flex items-center gap-3">
                <Link href="/" className="flex items-center gap-2 text-lg font-bold gradient-text-elegant hover:scale-105 transition-transform">
                  <div className="w-12 h-12 flex items-center justify-center">
                    <img 
                      src="/logo.svg" 
                      alt="QYRAL Logo" 
                      className="w-12 h-12"
                      style={{ filter: 'none' }}
                    />
                  </div>
                  QYRAL AI
                </Link>
              </div>
              <div className="flex items-center gap-2">
                {isAuthenticated && (
                  <>
                    <Link href="/workflows" className="btn-glass px-3 py-2 rounded-lg">Mis Workflows</Link>
                    <Link href="/chat" className="btn-primary px-3 py-2 rounded-lg">Crear Workflow</Link>
                  </>
                )}
                <button className="btn-glass px-3 py-2 rounded-lg opacity-50 cursor-not-allowed" disabled>
                  Marketplace - Próximamente
                </button>
                <button className="btn-glass px-3 py-2 rounded-lg opacity-50 cursor-not-allowed" disabled>
                  Agents - Próximamente
                </button>
                {!isAuthenticated && (
                  <button
                    onClick={() => setShowLoginModal(true)}
                    className="btn-primary px-4 py-2 rounded-lg font-semibold"
                  >
                    🔑 Iniciar Sesión
                  </button>
                )}
              </div>
            </div>

          </div>
        )}

        <div className="flex-1 overflow-hidden">
          <ErrorBoundary>
            <Router>
              <Dashboard 
                path="/" 
                isAuthenticated={isAuthenticated}
                onLoginClick={() => setShowLoginModal(true)}
              />
              <ChatView path="/chat" />
              <ChatView path="/chat/:chatId" />
              <WorkflowsPage path="/workflows" />
              <ExecutionsList path="/executions" />
              <ExecutionDetail path="/executions/:id" />
              <MarketplacePage path="/marketplace" />
              <AgentsPage path="/agents" />
              <AgentDetail path="/agents/:agentId" />
              <OAuthCallback path="/oauth-callback" />
            </Router>
          </ErrorBoundary>
        </div>
      </div>

      {showLoginModal && (
        <LoginForm onClose={() => setShowLoginModal(false)} />
      )}

      <CredentialsManager
        isOpen={showCredModal && isAuthenticated}
        onClose={() => setShowCredModal(false)}
        chatId={activeChatId}
      />

      <DeployAgentModal
        isOpen={showDeployModal && isAuthenticated}
        onClose={() => setShowDeployModal(false)}
      />
      <Notifications />
    </div>
  );
}

// Nombrar el componente explícitamente para Prefresh
App.displayName = 'App';

export default App;
