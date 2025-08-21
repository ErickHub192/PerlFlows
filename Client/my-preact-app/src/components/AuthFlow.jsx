import { useState, useEffect } from 'preact/hooks';
import { fetcher } from '../api/fetcher';
import useOAuthApps from '../hooks/useOAuthApps';

const AuthFlow = ({ isOpen, onClose, onSuccess, serviceId, chatId }) => {
    const [step, setStep] = useState('loading');
    const [authData, setAuthData] = useState(null);
    const [formData, setFormData] = useState({});
    const [error, setError] = useState(null);
    const [showOAuthConfig, setShowOAuthConfig] = useState(false);
    const [oauthFormData, setOAuthFormData] = useState({ client_id: '', client_secret: '', app_name: '' });
    
    const { createOAuthApp, hasOAuthApp } = useOAuthApps();

    useEffect(() => {
        if (isOpen && serviceId) {
            initiateAuth();
        }
    }, [isOpen, serviceId]);

    const initiateAuth = async () => {
        try {
            setStep('loading');
            setError(null);

            // ✅ NUEVO: Usar el sistema agnóstico - obtener auth step para el servicio
            const stepResponse = await fetcher(`/api/v1/auth-service-discovery/service/${serviceId}/auth-step?chat_id=${chatId || 'temp-chat'}`, {
                method: 'POST'
            });

            const authStep = stepResponse;
            
            if (!authStep) {
                // Ya está autenticado o no requiere auth
                setStep('success');
                setTimeout(() => {
                    onSuccess({ 
                        message: 'Already authenticated',
                        shouldResendMessage: true 
                    });
                    onClose();
                }, 1500);
                return;
            }

            setAuthData(authStep);

            // Decidir flujo basado en el mechanism
            if (authStep.mechanism === 'oauth2') {
                // Para OAuth, primero mostrar configuración opcional
                setStep('oauth_config');
                return;
            } else {
                // Form flow para API keys, bot tokens, etc.
                setStep('form');
            }
        } catch (err) {
            setError(err.message);
            setStep('error');
        }
    };

    const checkAuthStatus = async () => {
        try {
            setStep('checking');
            
            // Check if credentials exist for this service
            const response = await fetcher(`/api/v1/auth-service-discovery/service/${serviceId}/auth-step?chat_id=${chatId || 'temp-chat'}`, {
                method: 'POST'
            });

            if (!response) {
                // No auth step needed = already authenticated
                setStep('success');
                setTimeout(() => {
                    onSuccess({ 
                        message: 'OAuth successful',
                        shouldResendMessage: true 
                    });
                    onClose();
                }, 1500);
            } else {
                // Still needs auth, show error
                setError('OAuth flow was not completed. Please try again.');
                setStep('error');
            }
        } catch (err) {
            setError('Failed to verify authentication status.');
            setStep('error');
        }
    };

    const handleFormSubmit = async (e) => {
        e.preventDefault();
        try {
            setStep('processing');

            // ✅ NUEVO: Usar API de credentials agnóstica
            const credentialData = {
                service_id: serviceId,
                provider: authData.mechanism === 'oauth2' ? serviceId : serviceId,
                mechanism: authData.mechanism,
                config: formData,
                chat_id: chatId || 'temp-chat'
            };

            const response = await fetcher('/api/credentials/', {
                method: 'POST',
                body: credentialData
            });

            const result = response;
            setStep('success');
            
            setTimeout(() => {
                onSuccess(result);
                onClose();
            }, 1500);

        } catch (err) {
            setError(err.message);
            setStep('error');
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleOAuthConfigSubmit = async (useCustom) => {
        try {
            if (useCustom) {
                // Validar campos requeridos
                if (!oauthFormData.client_id || !oauthFormData.client_secret) {
                    setError('Client ID y Client Secret son requeridos');
                    return;
                }

                // Usar el provider que viene del authStep (ya resuelto por la infraestructura)
                const provider = authData.provider || serviceId;
                
                // Crear OAuth app si no existe
                if (!hasOAuthApp(provider)) {
                    await createOAuthApp(provider, {
                        client_id: oauthFormData.client_id,
                        client_secret: oauthFormData.client_secret,
                        app_name: oauthFormData.app_name || `${serviceId} OAuth App`
                    });
                }
            }
            
            // Proceder con OAuth flow
            proceedWithOAuth();
            
        } catch (err) {
            setError(err.message);
        }
    };

    const proceedWithOAuth = () => {
        // OAuth flow - wait 5 seconds for user to read LLM message, then open popup
        
        // Close modal immediately and wait for delay
        onClose();
        
        setTimeout(() => {
            // Get JWT token from localStorage for browser redirect
            const token = localStorage.getItem('access_token');
            const oauthUrl = `/api/oauth/initiate?service_id=${serviceId}&chat_id=${chatId || 'temp-chat'}&token=${token}`;
            
            // Open popup after delay
            const popup = window.open(
                oauthUrl,
                'oauth_popup',
                'width=500,height=600,scrollbars=yes,resizable=yes,menubar=no,toolbar=no,location=yes,status=no'
            );

            // Check if popup was blocked
            if (!popup || popup.closed || typeof popup.closed === 'undefined') {
                alert('Popup bloqueado por el navegador. Por favor permite ventanas emergentes y reintenta.');
                return;
            }
            
            // Declare interval variable first
            let checkClosed;

            // Setup global listeners for popup communication
            const messageListener = (event) => {
                // Verify origin for security (allow backend origin)
                const allowedOrigins = [window.location.origin, 'http://localhost:5000'];
                if (!allowedOrigins.includes(event.origin)) {
                    console.warn('OAuth message from unknown origin:', event.origin);
                    return;
                }

                if (event.data?.type === 'OAUTH_SUCCESS') {
                    console.log('OAuth success message received:', event.data);
                    window.removeEventListener('message', messageListener);
                    if (checkClosed) clearInterval(checkClosed);
                    try {
                        popup.close();
                    } catch (e) {
                        // Ignore cross-origin close errors
                    }
                    
                    // Call success callback
                    onSuccess({ message: 'OAuth successful' });
                } else if (event.data?.type === 'OAUTH_ERROR') {
                    console.error('OAuth error message received:', event.data);
                    window.removeEventListener('message', messageListener);
                    if (checkClosed) clearInterval(checkClosed);
                    try {
                        popup.close();
                    } catch (e) {
                        // Ignore cross-origin close errors
                    }
                    
                    // Show error as alert since modal is closed
                    alert('Error durante la autenticación OAuth: ' + (event.data.error || 'Error desconocido'));
                }
            };

            window.addEventListener('message', messageListener);
            
            // Fallback: Listen for popup close (handle cross-origin errors)
            checkClosed = setInterval(() => {
                try {
                    if (popup.closed) {
                        clearInterval(checkClosed);
                        window.removeEventListener('message', messageListener);
                        console.log('OAuth popup closed without success message');
                    }
                } catch (error) {
                    // Cross-origin error is expected, ignore it
                    // The popup will send postMessage when done
                }
            }, 1000);
        }, 5000);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="glass-card p-8 w-[500px] max-w-[90vw] max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-semibold text-elegant gradient-text">
                        Autenticar {authData?.service_name || serviceId}
                    </h2>
                    <button 
                        onClick={onClose} 
                        className="text-subtle hover:text-white transition-colors p-2 hover:bg-white hover:bg-opacity-10 rounded-lg"
                    >
                        ×
                    </button>
                </div>

                {step === 'loading' && (
                    <div className="text-center py-12">
                        <div className="text-subtle">Cargando configuración...</div>
                    </div>
                )}

                {step === 'oauth_waiting' && (
                    <div className="text-center py-12">
                        <div className="text-elegant mb-2">Abriendo ventana de autenticación...</div>
                        <div className="text-xs text-muted mt-2">
                            Se está abriendo una ventana para autenticar con {authData?.service_name || serviceId}
                        </div>
                        <div className="flex justify-center mt-6">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white border-opacity-30"></div>
                        </div>
                    </div>
                )}

                {step === 'oauth_config' && authData && (
                    <div className="space-y-6">
                        <div className="text-center mb-6">
                            <h3 className="text-lg font-medium text-elegant gradient-text">Configurar OAuth</h3>
                            <p className="text-sm text-subtle mt-2">
                                Puedes usar tus propias credenciales OAuth o las por defecto del sistema
                            </p>
                        </div>
                        
                        {showOAuthConfig ? (
                            <div className="space-y-5">
                                <div>
                                    <label className="block text-sm font-medium text-elegant mb-2">
                                        Nombre de la App (Opcional)
                                    </label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-3 surface-input text-white placeholder-gray-400 rounded-lg focus-elegant transition-all"
                                        placeholder="Mi App de Gmail"
                                        value={oauthFormData.app_name}
                                        onChange={(e) => setOAuthFormData({...oauthFormData, app_name: e.target.value})}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-elegant mb-2">
                                        Client ID *
                                    </label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-3 surface-input text-white placeholder-gray-400 rounded-lg focus-elegant transition-all"
                                        placeholder="123456789-abcdef.apps.googleusercontent.com"
                                        value={oauthFormData.client_id}
                                        onChange={(e) => setOAuthFormData({...oauthFormData, client_id: e.target.value})}
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-elegant mb-2">
                                        Client Secret *
                                    </label>
                                    <input
                                        type="password"
                                        className="w-full px-4 py-3 surface-input text-white placeholder-gray-400 rounded-lg focus-elegant transition-all"
                                        placeholder="GOCSPX-1234567890abcdef"
                                        value={oauthFormData.client_secret}
                                        onChange={(e) => setOAuthFormData({...oauthFormData, client_secret: e.target.value})}
                                        required
                                    />
                                </div>
                                <div className="surface-elevated rounded-xl p-4 mb-4">
                                    <p className="text-elegant text-sm font-medium mb-3">
                                        📋 <strong>Importante:</strong> Configura esta Redirect URI en tu OAuth App:
                                    </p>
                                    <div className="flex items-center gap-3">
                                        <code className="flex-1 text-white bg-black bg-opacity-40 px-3 py-2 rounded-lg text-xs font-mono break-all border border-white border-opacity-20">
                                            https://perlflow.com/api/oauth/callback
                                        </code>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                navigator.clipboard.writeText('https://perlflow.com/api/oauth/callback');
                                                // Feedback visual temporal
                                                const btn = event.target;
                                                const originalText = btn.textContent;
                                                btn.textContent = '✅';
                                                setTimeout(() => btn.textContent = originalText, 1000);
                                            }}
                                            className="btn-glass px-3 py-2 text-white hover:text-white rounded-lg transition-all"
                                            title="Copiar al clipboard"
                                        >
                                            📋
                                        </button>
                                    </div>
                                    <p className="text-subtle text-xs mt-3">
                                        💡 Los scopes se configuran automáticamente según el tipo de credencial
                                    </p>
                                </div>
                                <div className="flex space-x-3">
                                    <button
                                        type="button"
                                        onClick={() => setShowOAuthConfig(false)}
                                        className="flex-1 btn-secondary px-4 py-3 rounded-lg transition-all"
                                    >
                                        Cancelar
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleOAuthConfigSubmit(true)}
                                        className="flex-1 btn-primary px-4 py-3 rounded-lg transition-all"
                                    >
                                        Usar mis credenciales
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <button
                                    type="button"
                                    onClick={() => setShowOAuthConfig(true)}
                                    className="w-full px-6 py-4 border-2 border-dashed border-white border-opacity-30 text-elegant rounded-xl hover:border-opacity-50 hover:bg-white hover:bg-opacity-5 transition-all"
                                >
                                    🔧 Configurar mis credenciales OAuth
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleOAuthConfigSubmit(false)}
                                    className="w-full btn-primary px-6 py-4 rounded-xl"
                                >
                                    Usar credenciales por defecto
                                </button>
                            </div>
                        )}
                        
                        {error && (
                            <div className="surface-elevated border border-red-400 border-opacity-30 rounded-lg p-3 mt-4">
                                <div className="text-red-300 text-sm">{error}</div>
                            </div>
                        )}
                    </div>
                )}

                {step === 'oauth_popup' && (
                    <div className="text-center py-8">
                        <div className="text-gray-500">Ventana OAuth abierta...</div>
                        <div className="text-xs text-gray-400 mt-2">
                            Completa la autenticación en la ventana emergente.
                            <br />Si no se abrió, verifica que tu navegador permita ventanas emergentes.
                        </div>
                    </div>
                )}

                {step === 'checking' && (
                    <div className="text-center py-8">
                        <div className="text-gray-500">Verificando autenticación...</div>
                    </div>
                )}

                {step === 'redirecting' && (
                    <div className="text-center py-8">
                        <div className="text-gray-500">Redirigiendo a {authData?.service_name}...</div>
                        <div className="text-xs text-gray-400 mt-2">
                            Si no fuiste redirigido automáticamente, 
                            <a href={authData?.auth_url} className="text-blue-500 underline ml-1">
                                haz clic aquí
                            </a>
                        </div>
                    </div>
                )}

                {step === 'form' && authData && (
                    <form onSubmit={handleFormSubmit} className="space-y-4">
                        {/* ✅ NUEVO: Usar campos del authStep agnóstico */}
                        {authData.metadata?.fields?.map((field, index) => (
                            <div key={index}>
                                <label className="block text-sm font-medium text-elegant mb-2">
                                    {field.label || field.name?.charAt(0).toUpperCase() + field.name?.slice(1).replace('_', ' ')}
                                </label>
                                <input
                                    type={field.type || (field.name?.includes('password') || field.name?.includes('key') || field.name?.includes('token') ? 'password' : 'text')}
                                    className="w-full px-4 py-3 surface-input text-white placeholder-gray-400 rounded-lg focus-elegant transition-all"
                                    placeholder={field.placeholder || `Ingresa tu ${field.name}...`}
                                    value={formData[field.name] || ''}
                                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                                    required={field.required !== false}
                                />
                                {field.help_text && (
                                    <p className="text-xs text-gray-500 mt-1">{field.help_text}</p>
                                )}
                            </div>
                        )) || 
                        // Fallback para mechanisms simples
                        (authData.mechanism === 'api_key' && (
                            <div>
                                <label className="block text-sm font-medium text-elegant mb-2">
                                    API Key
                                </label>
                                <input
                                    type="password"
                                    className="w-full px-4 py-3 surface-input text-white placeholder-gray-400 rounded-lg focus-elegant transition-all"
                                    placeholder="Ingresa tu API Key..."
                                    value={formData.api_key || ''}
                                    onChange={(e) => handleInputChange('api_key', e.target.value)}
                                    required
                                />
                            </div>
                        )) ||
                        (authData.mechanism === 'bot_token' && (
                            <div>
                                <label className="block text-sm font-medium text-elegant mb-2">
                                    Bot Token
                                </label>
                                <input
                                    type="password"
                                    className="w-full px-4 py-3 surface-input text-white placeholder-gray-400 rounded-lg focus-elegant transition-all"
                                    placeholder="Ingresa tu Bot Token..."
                                    value={formData.bot_token || ''}
                                    onChange={(e) => handleInputChange('bot_token', e.target.value)}
                                    required
                                />
                            </div>
                        ))}
                        <button
                            type="submit"
                            className="w-full btn-primary px-4 py-3 rounded-lg transition-all"
                        >
                            Conectar
                        </button>
                    </form>
                )}

                {step === 'processing' && (
                    <div className="text-center py-8">
                        <div className="text-gray-500">Procesando...</div>
                    </div>
                )}

                {step === 'success' && (
                    <div className="text-center py-8">
                        <div className="text-green-600">¡Conexión exitosa!</div>
                    </div>
                )}

                {step === 'error' && (
                    <div className="text-center py-8">
                        <div className="text-red-600 mb-4">Error: {error}</div>
                        <button
                            onClick={initiateAuth}
                            className="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600"
                        >
                            Reintentar
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AuthFlow;