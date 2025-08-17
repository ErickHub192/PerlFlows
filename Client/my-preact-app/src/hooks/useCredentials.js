import { useState, useEffect } from 'preact/hooks';
import { getToken } from './useAuth';

const useCredentials = () => {
    const [credentials, setCredentials] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchCredentials = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const response = await fetch('/api/credentials/', {
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const data = await response.json();
            setCredentials(data);
            return data;
            
        } catch (err) {
            setError(err.message);
            return [];
        } finally {
            setLoading(false);
        }
    };

    const getCredential = async (provider, flavor = null) => {
        try {
            const params = new URLSearchParams({ provider });
            if (flavor) params.append('flavor', flavor);

            const response = await fetch(`/api/credentials/${provider}?${params.toString()}`, {
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (response.status === 404) {
                return null; // No existe credencial
            }

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            return await response.json();
            
        } catch (err) {
            console.error('Error getting credential:', err);
            return null;
        }
    };

    const createCredential = async (credentialData) => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/credentials/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getToken()}`
                },
                body: JSON.stringify(credentialData)
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const newCredential = await response.json();
            
            // Actualizar lista de credenciales
            setCredentials(prev => {
                const filtered = prev.filter(c => 
                    !(c.provider === newCredential.provider && c.flavor === newCredential.flavor)
                );
                return [...filtered, newCredential];
            });

            return newCredential;
            
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const deleteCredential = async (serviceIdOrProvider, flavor = null) => {
        try {
            setLoading(true);
            setError(null);

            // ✅ FIX: Determinar si usar nuevo formato (service_id) o legacy (provider+flavor)
            let url;
            let credentialToDelete;
            
            if (flavor !== null) {
                // ❌ LEGACY: provider + flavor (deprecado)
                console.warn('⚠️ Using deprecated provider+flavor deletion. Please migrate to service_id.');
                url = `/api/credentials/${serviceIdOrProvider}?flavor=${flavor}`;
                credentialToDelete = (c) => c.provider === serviceIdOrProvider && c.flavor === flavor;
            } else {
                // ✅ NEW: service_id único
                url = `/api/credentials/${serviceIdOrProvider}`;
                credentialToDelete = (c) => c.service_id === serviceIdOrProvider;
            }

            console.log('🗑️ Deleting credential:', { serviceIdOrProvider, flavor, url });

            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            // ✅ FIX: Actualizar lista solo después de confirmación del backend
            console.log('✅ Credencial eliminada exitosamente del backend');
            setCredentials(prev => prev.filter(c => !credentialToDelete(c)));

            return true;
            
        } catch (err) {
            console.error('❌ Error eliminando credencial:', err);
            setError(err.message);
            
            // ✅ FIX: Recargar credenciales desde servidor para mantener sincronización
            console.log('🔄 Recargando credenciales desde servidor para sincronizar...');
            await fetchCredentials();
            
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const hasCredential = (provider, flavor = null) => {
        return credentials.some(c => 
            c.provider === provider && 
            (flavor === null || c.flavor === flavor)
        );
    };

    const refreshCredentials = () => {
        return fetchCredentials();
    };

    // ✅ REFACTORIZADO: Helper agnóstico para determinar estado de conexión
    const getConnectionStatus = (serviceIdOrProvider, flavor = null) => {
        // Buscar por service_id (nuevo) o provider+flavor (legacy)
        const cred = credentials.find(c => 
            c.service_id === serviceIdOrProvider || 
            (c.provider === serviceIdOrProvider && (flavor === null || c.flavor === flavor))
        );
        
        if (!cred) return 'disconnected';
        
        // Verificar si el token está expirado (si tiene información de expiración)
        if (cred.expires_at) {
            const expiresAt = new Date(cred.expires_at);
            const now = new Date();
            
            if (expiresAt <= now) {
                return 'expired';
            }
        }
        
        return 'connected';
    };

    // Helper para obtener scopes/permisos disponibles
    const getCredentialScopes = (provider, flavor = null) => {
        const cred = credentials.find(c => 
            c.provider === provider && 
            (flavor === null || c.flavor === flavor)
        );
        
        return cred?.scopes || [];
    };

    // Cargar credenciales al montar el hook solo si hay token
    useEffect(() => {
        const token = getToken();
        if (token) {
            fetchCredentials();
        }
    }, []);

    return {
        credentials,
        loading,
        error,
        fetchCredentials,
        getCredential,
        createCredential,
        deleteCredential,
        hasCredential,
        refreshCredentials,
        getConnectionStatus,
        getCredentialScopes
    };
};

export default useCredentials;