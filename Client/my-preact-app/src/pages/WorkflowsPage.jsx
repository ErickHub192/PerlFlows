import { useState, useEffect } from 'preact/hooks';
import useWorkflows from '../hooks/useWorkflows';
import WorkflowsList from '../components/WorkflowsList';
import CredentialsManager from '../components/CredentialsManager';
import { useAuth } from '../hooks/useAuth';
import { route } from 'preact-router';

export default function WorkflowsPage() {
  // — Auth check —
  const { token } = useAuth();
  const isAuthenticated = !!token;

  // Redirect to home if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      route('/', true);
      return;
    }
  }, [isAuthenticated]);

  // Don't render if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  const { workflows, loading, error, deleteWorkflow } = useWorkflows();
  const [showCredentialsManager, setShowCredentialsManager] = useState(false);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  
  const handleCreateWorkflow = () => {
    if (isCreatingChat) return;
    
    setIsCreatingChat(true);
    try {
      route('/chat', true);
    } catch (err) {
      console.error('Error navegando a nuevo chat:', err);
      alert('Error iniciando nuevo workflow. Por favor intenta de nuevo.');
    } finally {
      setIsCreatingChat(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-main flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-purple rounded-3xl flex items-center justify-center text-3xl mx-auto mb-4">
            ⚡
          </div>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-text-secondary">Cargando workflows...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-main flex items-center justify-center">
        <div className="glass rounded-3xl p-8 text-center max-w-md">
          <div className="w-16 h-16 bg-red-500/20 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
            ⚠️
          </div>
          <h3 className="text-xl font-bold text-text-primary mb-2">Error al cargar workflows</h3>
          <p className="text-text-secondary mb-6">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="btn-primary px-6 py-3 rounded-lg font-medium"
          >
            🔄 Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-main text-text-primary">
      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="glass border-b border-purple-500/20 p-6 rounded-t-3xl mb-8">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-purple rounded-xl flex items-center justify-center text-2xl">
                🚀
              </div>
              <div>
                <h1 className="text-3xl font-bold gradient-text">Mis Workflows</h1>
                <p className="text-text-secondary">Gestiona y crea tus automatizaciones</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowCredentialsManager(true)}
                className="btn-glass px-4 py-2 rounded-lg font-medium"
              >
                🔐 Gestionar Credenciales
              </button>
              <button
                onClick={handleCreateWorkflow}
                disabled={isCreatingChat}
                className="btn-primary px-4 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreatingChat ? '⏳ Creando...' : '➕ Crear Workflow'}
              </button>
            </div>
          </div>
        </div>
      
        {workflows.length === 0 ? (
          <div className="glass rounded-3xl p-12 text-center">
            <div className="w-24 h-24 bg-gradient-purple rounded-3xl flex items-center justify-center text-4xl mb-6 opacity-80 mx-auto">
              💾
            </div>
            <h3 className="text-2xl font-bold gradient-text mb-3">No tienes workflows guardados</h3>
            <p className="text-text-secondary max-w-md mx-auto leading-relaxed mb-4">
              Los workflows son automatizaciones completadas y guardadas que puedes reutilizar.
            </p>
            <div className="bg-blue-500/10 border border-blue-400/30 rounded-xl p-4 mb-8 text-left max-w-lg mx-auto">
              <h4 className="text-blue-300 font-semibold mb-2">💡 ¿Cómo crear workflows?</h4>
              <ol className="text-sm text-text-secondary space-y-1">
                <li>1. Crea un chat nuevo desde el sidebar izquierdo</li>
                <li>2. Describe tu automatización en lenguaje natural</li>
                <li>3. QYRAL AI configurará los pasos automáticamente</li>
                <li>4. Al finalizar, guarda el workflow para reutilizarlo</li>
              </ol>
            </div>
            <button
              onClick={handleCreateWorkflow}
              disabled={isCreatingChat}
              className="btn-primary px-8 py-4 rounded-2xl font-bold text-lg shadow-purple-lg hover:transform hover:scale-105 transition-all duration-300 inline-flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {isCreatingChat ? (
                <>
                  ⏳ Abriendo chat...
                </>
              ) : (
                <>
                  💬 Abrir Chat para Crear Workflow
                </>
              )}
            </button>
          </div>
        ) : (
          <WorkflowsList flows={workflows} onDeleteWorkflow={deleteWorkflow} />
        )}

        {/* Credentials Manager Modal */}
        <CredentialsManager
          isOpen={showCredentialsManager}
          onClose={() => setShowCredentialsManager(false)}
        />
      </div>
    </div>
  );
}
