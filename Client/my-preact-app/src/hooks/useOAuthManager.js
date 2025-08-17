import { useState, useEffect } from 'preact/hooks';
import useCredentials from './useCredentials';
import { useUnifiedAuth } from '../services/unifiedAuthService';

const useOAuthManager = () => {
    const [pendingOAuthRequests, setPendingOAuthRequests] = useState([]);
    const [isProcessingOAuth, setIsProcessingOAuth] = useState(false);
    
    const { credentials, refreshCredentials, hasCredential } = useCredentials();
    const { checkOAuthRequirements, formatStepsForUnifiedAPI } = useUnifiedAuth();

    // ✅ MIGRADO: Añadir requests usando nueva API unificada
    const addOAuthRequests = (oauthRequirements) => {
        if (!oauthRequirements || oauthRequirements.length === 0) {
            return;
        }

        const newRequests = oauthRequirements.map(req => ({
            id: `${req.provider || req.node_id}_${req.flavor || req.service || ''}`,
            provider: req.provider || req.node_id?.split('_')[0] || 'unknown',
            flavor: req.flavor || req.service || null,
            authUrl: req.authorization_url || req.oauth_url,
            scopes: req.scopes || [],
            displayName: req.display_name || req.provider || 'Unknown Service',
            priority: req.priority || 1,
            status: 'pending', // pending, processing, completed, error
            // ✅ NUEVO: Campos adicionales de la unified API
            service: req.service,
            total_scopes_needed: req.scopes?.length || 0,
            metadata: req.metadata || {}
        }));

        setPendingOAuthRequests(prev => {
            // Evitar duplicados
            const existing = new Set(prev.map(r => r.id));
            const filtered = newRequests.filter(r => !existing.has(r.id));
            return [...prev, ...filtered];
        });
    };
    
    // ✅ NUEVA FUNCIÓN: Añadir requests desde workflow steps usando unified API
    const addOAuthRequestsFromWorkflow = async (workflowSteps) => {
        if (!workflowSteps || workflowSteps.length === 0) {
            return;
        }
        
        try {
            setIsProcessingOAuth(true);
            const formattedSteps = formatStepsForUnifiedAPI(workflowSteps);
            const requirements = await checkOAuthRequirements(formattedSteps);
            
            if (requirements.missing_oauth && requirements.missing_oauth.length > 0) {
                addOAuthRequests(requirements.missing_oauth);
            }
            
            return requirements;
        } catch (error) {
            console.error('Error adding OAuth requests from workflow:', error);
            throw error;
        } finally {
            setIsProcessingOAuth(false);
        }
    };

    const markAsCompleted = (providerId) => {
        setPendingOAuthRequests(prev => 
            prev.map(req => 
                req.id === providerId 
                    ? { ...req, status: 'completed' }
                    : req
            )
        );
    };

    const markAsError = (providerId, error) => {
        setPendingOAuthRequests(prev => 
            prev.map(req => 
                req.id === providerId 
                    ? { ...req, status: 'error', error: error?.message || 'Unknown error' }
                    : req
            )
        );
    };

    const retryRequest = (providerId) => {
        setPendingOAuthRequests(prev => 
            prev.map(req => 
                req.id === providerId 
                    ? { ...req, status: 'pending', error: null }
                    : req
            )
        );
    };

    const clearCompleted = () => {
        setPendingOAuthRequests(prev => 
            prev.filter(req => req.status !== 'completed')
        );
    };

    const clearAll = () => {
        setPendingOAuthRequests([]);
    };

    const checkIfAlreadyAuthorized = async (provider, flavor) => {
        await refreshCredentials();
        return hasCredential(provider, flavor);
    };

    // Auto-remove completed requests after delay
    useEffect(() => {
        const completedRequests = pendingOAuthRequests.filter(req => req.status === 'completed');
        
        if (completedRequests.length > 0) {
            const timer = setTimeout(() => {
                clearCompleted();
            }, 5000); // Remove after 5 seconds

            return () => clearTimeout(timer);
        }
    }, [pendingOAuthRequests]);

    // Helper para obtener stats
    const getStats = () => {
        const pending = pendingOAuthRequests.filter(req => req.status === 'pending').length;
        const processing = pendingOAuthRequests.filter(req => req.status === 'processing').length;
        const completed = pendingOAuthRequests.filter(req => req.status === 'completed').length;
        const errors = pendingOAuthRequests.filter(req => req.status === 'error').length;

        return {
            total: pendingOAuthRequests.length,
            pending,
            processing,
            completed,
            errors,
            allCompleted: pending === 0 && processing === 0 && errors === 0 && pendingOAuthRequests.length > 0,
            // ✅ NUEVAS STATS
            completion_percentage: pendingOAuthRequests.length > 0 ? (completed / pendingOAuthRequests.length) * 100 : 0,
            has_errors: errors > 0,
            ready_to_execute: pending === 0 && processing === 0 && errors === 0
        };
    };

    const hasPendingRequests = () => {
        return pendingOAuthRequests.some(req => 
            req.status === 'pending' || req.status === 'processing'
        );
    };

    return {
        pendingOAuthRequests,
        isProcessingOAuth,
        setIsProcessingOAuth,
        addOAuthRequests,
        addOAuthRequestsFromWorkflow, // ✅ NUEVA FUNCIÓN
        markAsCompleted,
        markAsError,
        retryRequest,
        clearCompleted,
        clearAll,
        checkIfAlreadyAuthorized,
        getStats,
        hasPendingRequests
    };
};

export default useOAuthManager;