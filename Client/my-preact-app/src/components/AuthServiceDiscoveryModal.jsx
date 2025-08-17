import { useState, useEffect } from 'preact/hooks';

const AuthServiceDiscoveryModal = ({ isOpen, onClose, userIntent, onServiceSelected }) => {
  const [discoveryResults, setDiscoveryResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && userIntent) {
      performAuthServiceDiscovery();
    }
  }, [isOpen, userIntent]);

  const performAuthServiceDiscovery = async () => {
    if (!userIntent?.trim()) return;

    setIsLoading(true);
    setError(null);
    
    try {
      const { fetcher } = await import('../api/fetcher');
      
      const data = await fetcher('/api/v1/auth-service-discovery/auto-discover', {
        method: 'POST',
        body: {
          user_intent: userIntent,
          context: 'auth_service_discovery'
        }
      });

      setDiscoveryResults(data.suggestions || []);
    } catch (err) {
      console.error('Auth service discovery error:', err);
      setError(err.detail?.[0]?.msg || err.message || 'Error en el descubrimiento de servicios de auth');
    } finally {
      setIsLoading(false);
    }
  };

  const handleServiceSelect = (service) => {
    // Trigger service selection for authentication setup
    onServiceSelected && onServiceSelected({
      service_id: service.service_id,
      service_name: service.name,
      mechanism: service.mechanism,
      provider: service.provider,
      suggested_actions: service.suggested_actions || []
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Descubrimiento de Servicios de Autenticación
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Intent detectado:</span> {userIntent}
          </p>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-gray-600">Analizando servicios de autenticación disponibles...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        {!isLoading && !error && discoveryResults.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500">No se encontraron servicios de autenticación relevantes para este intent.</p>
          </div>
        )}

        {discoveryResults.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900">Servicios de Autenticación Disponibles:</h4>
            {discoveryResults.map((service, index) => (
              <div
                key={service.service_id || index}
                className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => handleServiceSelect(service)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h5 className="font-medium text-gray-900">
                      {service.name || service.service_id}
                    </h5>
                    <p className="text-sm text-gray-600 mt-1">
                      {service.description || 'Servicio de autenticación disponible'}
                    </p>
                    
                    <div className="mt-2 flex flex-wrap gap-2">
                      <span className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded">
                        {service.mechanism || 'oauth2'}
                      </span>
                      {service.provider && (
                        <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                          {service.provider}
                        </span>
                      )}
                    </div>

                    {service.suggested_actions && service.suggested_actions.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-gray-500">Acciones sugeridas:</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {service.suggested_actions.slice(0, 3).map((action, actionIndex) => (
                            <span
                              key={actionIndex}
                              className="inline-block bg-green-100 text-green-800 text-xs px-2 py-1 rounded"
                            >
                              {action.name || action}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="ml-4 flex-shrink-0">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {service.confidence ? `${Math.round(service.confidence * 100)}%` : 'Disponible'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end space-x-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          >
            Cerrar
          </button>
          {discoveryResults.length > 0 && (
            <button
              onClick={performAuthServiceDiscovery}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              Refrescar Servicios
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthServiceDiscoveryModal;