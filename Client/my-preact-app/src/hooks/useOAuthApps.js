import { useState, useEffect } from 'preact/hooks';
import { getToken } from './useAuth';

/**
 * Hook para gestionar OAuth Applications del usuario
 */
const useOAuthApps = () => {
    const [oauthApps, setOauthApps] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Cargar OAuth apps del usuario
    const fetchOAuthApps = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const token = getToken();
            const response = await fetch('/api/oauth-apps/', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${await response.text()}`);
            }

            const data = await response.json();
            setOauthApps(data.oauth_apps || []);
            
        } catch (err) {
            console.error('Error fetching OAuth apps:', err);
            setError(err.message);
            setOauthApps([]);
        } finally {
            setLoading(false);
        }
    };

    // Crear nueva OAuth app
    const createOAuthApp = async (provider, { client_id, client_secret, app_name }) => {
        try {
            setLoading(true);
            setError(null);

            const token = getToken();
            const response = await fetch(`/api/oauth-apps/${provider}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    provider,
                    client_id,
                    client_secret,
                    app_name
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            const newApp = await response.json();
            
            // Actualizar lista local
            setOauthApps(prev => {
                const filtered = prev.filter(app => app.provider !== provider);
                return [...filtered, newApp];
            });

            return newApp;
            
        } catch (err) {
            console.error('Error creating OAuth app:', err);
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Actualizar OAuth app existente
    const updateOAuthApp = async (provider, updateData) => {
        try {
            setLoading(true);
            setError(null);

            const token = getToken();
            const response = await fetch(`/api/oauth-apps/${provider}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updateData)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            const updatedApp = await response.json();
            
            // Actualizar lista local
            setOauthApps(prev => prev.map(app => 
                app.provider === provider ? updatedApp : app
            ));

            return updatedApp;
            
        } catch (err) {
            console.error('Error updating OAuth app:', err);
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Eliminar OAuth app
    const deleteOAuthApp = async (provider) => {
        try {
            setLoading(true);
            setError(null);

            const token = getToken();
            const response = await fetch(`/api/oauth-apps/${provider}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            // Remover de lista local
            setOauthApps(prev => prev.filter(app => app.provider !== provider));

            return await response.json();
            
        } catch (err) {
            console.error('Error deleting OAuth app:', err);
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    };

    // Obtener OAuth app específica
    const getOAuthApp = async (provider) => {
        try {
            const token = getToken();
            const response = await fetch(`/api/oauth-apps/${provider}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.status === 404) {
                return null; // OAuth app no existe
            }

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            return await response.json();
            
        } catch (err) {
            console.error('Error getting OAuth app:', err);
            throw err;
        }
    };

    // Verificar si usuario tiene OAuth app para un provider
    const hasOAuthApp = (provider) => {
        return oauthApps.some(app => app.provider === provider);
    };

    // Obtener OAuth app local por provider
    const getLocalOAuthApp = (provider) => {
        return oauthApps.find(app => app.provider === provider);
    };

    // Auto-fetch al montar el hook
    useEffect(() => {
        fetchOAuthApps();
    }, []);

    return {
        oauthApps,
        loading,
        error,
        fetchOAuthApps,
        createOAuthApp,
        updateOAuthApp,
        deleteOAuthApp,
        getOAuthApp,
        hasOAuthApp,
        getLocalOAuthApp
    };
};

export default useOAuthApps;