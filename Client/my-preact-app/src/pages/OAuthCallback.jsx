import { useEffect, useState } from 'preact/hooks';
import { route } from 'preact-router';
import { getToken } from '../hooks/useAuth';

const OAuthCallback = () => {
    const [status, setStatus] = useState('processing');
    const [message, setMessage] = useState('Procesando autorización...');
    const [providerInfo, setProviderInfo] = useState(null);

    const processOAuthCallback = async (code, state, service) => {
        try {
            setMessage('Intercambiando código por tokens...');
            
            // If opened as popup, send success message to parent
            if (window.opener) {
                console.log('Popup detected - sending success message to parent');
                window.opener.postMessage({
                    oauth: 'success',
                    code,
                    state,
                    service
                }, window.location.origin);
                
                setStatus('success');
                setMessage('¡Autorización completada exitosamente!');
                
                // Close popup after short delay
                setTimeout(() => {
                    window.close();
                }, 2000);
                
                return; // Don't process further if popup
            }
            
            // Llamar al backend para procesar el callback (solo si no es popup)
            const params = new URLSearchParams({
                service: service,
                code: code
            });
            
            if (state) {
                params.append('state', state);
            }

            const response = await fetch(`/api/oauth/callback?${params.toString()}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${getToken()}` // JWT token si existe
                },
                credentials: 'include' // Para cookies de sesión
            });

            if (!response.ok) {
                // Si el backend retorna error, procesarlo
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            // El backend debe manejar el intercambio y almacenamiento
            // Si llegamos aquí, fue exitoso
            setStatus('success');
            setMessage('¡Credenciales guardadas exitosamente!');
            
            // Verificar si se crearon credenciales
            await verifyCredentials(service);
            
            // Redirigir después de éxito
            setTimeout(() => route('/'), 3000);
            
        } catch (error) {
            console.error('Error processing OAuth callback:', error);
            
            // If popup, send error to parent
            if (window.opener) {
                window.opener.postMessage({
                    oauth: 'error',
                    error: error.message
                }, window.location.origin);
                
                setTimeout(() => {
                    window.close();
                }, 2000);
                
                return;
            }
            
            setStatus('error');
            setMessage(`Error procesando autorización: ${error.message}`);
        }
    };

    const verifyCredentials = async (service) => {
        try {
            // Verificar que las credenciales se guardaron correctamente
            const response = await fetch(`/api/credentials/${service}`, {
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (response.ok) {
                const credential = await response.json();
                setProviderInfo({
                    service_id: credential.service_id,
                    created_at: credential.created_at
                });
                setMessage(`¡${credential.service_id.toUpperCase()} conectado exitosamente!`);
            }
        } catch (error) {
            console.log('Could not verify credentials, but OAuth might still be successful');
        }
    };

    const getServiceFromState = (state) => {
        try {
            // Si el state contiene información del servicio (formato JSON)
            const stateData = JSON.parse(atob(state));
            return stateData.service || stateData.provider;
        } catch {
            // Si no se puede parsear, asumir que es el servicio directamente
            return state;
        }
    };

    const extractServiceFromUrl = () => {
        // Intentar extraer el servicio de la URL de origen
        const referrer = document.referrer;
        const currentUrl = window.location.href;
        
        // Buscar patrones comunes
        const patterns = [
            /service=([^&]+)/,
            /provider=([^&]+)/,
            /\/oauth\/([^\/\?]+)/
        ];
        
        for (const pattern of patterns) {
            const match = (referrer + currentUrl).match(pattern);
            if (match) {
                return match[1];
            }
        }
        
        return null;
    };

    useEffect(() => {
        const processCallback = async () => {
            // Extraer parámetros de la URL
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            const state = urlParams.get('state');
            const error = urlParams.get('error');
            const error_description = urlParams.get('error_description');

            if (error) {
                const fullError = error_description ? `${error}: ${error_description}` : error;
                
                // If popup, send error to parent
                if (window.opener) {
                    window.opener.postMessage({
                        oauth: 'error',
                        error: fullError
                    }, window.location.origin);
                    
                    setTimeout(() => {
                        window.close();
                    }, 2000);
                    
                    return;
                }
                
                setStatus('error');
                setMessage(`Error en autorización: ${fullError}`);
                setTimeout(() => route('/'), 5000);
                return;
            }

            if (!code) {
                const errorMsg = 'No se recibió código de autorización';
                
                // If popup, send error to parent
                if (window.opener) {
                    window.opener.postMessage({
                        oauth: 'error',
                        error: errorMsg
                    }, window.location.origin);
                    
                    setTimeout(() => {
                        window.close();
                    }, 2000);
                    
                    return;
                }
                
                setStatus('error');
                setMessage(errorMsg);
                setTimeout(() => route('/'), 3000);
                return;
            }

            // Determinar el servicio/provider
            let service = null;
            
            if (state) {
                service = getServiceFromState(state);
            }
            
            if (!service) {
                service = extractServiceFromUrl();
            }
            
            if (!service) {
                // Fallback - intentar detectar por el dominio de origen
                const urlHostname = window.location.hostname;
                if (urlHostname.includes('google')) service = 'google';
                else if (urlHostname.includes('microsoft')) service = 'microsoft';
                else if (urlHostname.includes('slack')) service = 'slack';
                else service = 'unknown';
            }

            // Procesar el callback
            await processOAuthCallback(code, state, service);
        };

        processCallback();
    }, []);

    return (
        <div className="min-h-screen bg-gradient-main flex items-center justify-center">
            <div className="glass-card p-8 text-center max-w-md mx-4">
                {status === 'processing' && (
                    <>
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto mb-4"></div>
                        <h2 className="text-xl font-semibold text-elegant mb-2">Procesando autorización</h2>
                        <p className="text-subtle">{message}</p>
                    </>
                )}
                {status === 'success' && (
                    <>
                        <div className="text-green-500 text-6xl mb-4">✅</div>
                        <h2 className="text-xl font-semibold text-elegant mb-2">¡Autorización exitosa!</h2>
                        <p className="text-subtle mb-4">{message}</p>
                        {providerInfo && (
                            <div className="surface-elevated rounded-lg p-4 mb-4">
                                <div className="text-sm text-elegant">
                                    <div><strong>Servicio:</strong> {providerInfo.service_id}</div>
                                    <div><strong>Conectado:</strong> {new Date(providerInfo.created_at).toLocaleString()}</div>
                                </div>
                            </div>
                        )}
                        <p className="text-xs text-muted">
                            Redirigiendo automáticamente en unos segundos...
                        </p>
                    </>
                )}
                {status === 'error' && (
                    <>
                        <div className="text-red-500 text-6xl mb-4">❌</div>
                        <h2 className="text-xl font-semibold text-elegant mb-2">Error en autorización</h2>
                        <p className="text-subtle">{message}</p>
                    </>
                )}
            </div>
        </div>
    );
};

OAuthCallback.displayName = 'OAuthCallback';

export default OAuthCallback;