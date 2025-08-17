/**
 * 🔥 SERVICIO AGNÓSTICO UNIFICADO - Usa el nuevo sistema agnóstico
 * 
 * Reemplaza toda la lógica hardcodeada con el nuevo sistema escalable
 * que usa AutoAuthTrigger y Service Discovery APIs
 */

import { fetcher } from '../api/fetcher';

class UnifiedAuthService {
    constructor() {
        this.oauthBaseUrl = '/api/oauth';
        this.discoveryBaseUrl = '/api/v1/auth-service-discovery';
    }

    /**
     * ✅ NUEVA API AGNÓSTICA: Analiza workflow completo usando Service Discovery
     * 
     * @param {Object} flowSpec - Especificación completa del workflow
     * @param {string} chatId - ID del chat
     * @returns {Promise<{missing_oauth: Array, ready_to_execute: boolean}>}
     */
    async analyzeWorkflowAuthRequirements(flowSpec, chatId) {
        try {
            const response = await fetcher(`${this.discoveryBaseUrl}/workflow/analyze-auth`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    flow_spec: flowSpec,
                    chat_id: chatId
                })
            });

            if (!response.ok) {
                throw new Error(`Workflow auth analysis failed: ${response.status}`);
            }

            const analysis = await response.json();
            
            // Transformar a formato compatible con frontend
            return {
                missing_oauth: analysis.missing_requirements.map(req => ({
                    service_id: req.service_id,
                    provider: req.provider,
                    service: req.service,
                    mechanism: req.mechanism,
                    oauth_url: `${this.oauthBaseUrl}/initiate?service_id=${req.service_id}&chat_id=${chatId}`,
                    authorization_url: `${this.oauthBaseUrl}/initiate?service_id=${req.service_id}&chat_id=${chatId}`,
                    display_name: req.display_name || req.service_id,
                    scopes: req.required_scopes || [],
                    is_satisfied: req.is_satisfied
                })),
                satisfied_oauth: analysis.satisfied_requirements.map(req => ({
                    service_id: req.service_id,
                    provider: req.provider,
                    display_name: req.display_name,
                    is_satisfied: req.is_satisfied
                })),
                ready_to_execute: analysis.can_execute,
                total_services_needed: analysis.total_requirements,
                authenticated_count: analysis.satisfied_count,
                completion_percentage: analysis.total_requirements > 0 
                    ? (analysis.satisfied_count / analysis.total_requirements) * 100 
                    : 100,
                auto_triggered: analysis.auto_triggered,
                auth_steps: analysis.auth_steps || []
            };
        } catch (error) {
            console.error('Error analyzing workflow auth requirements:', error);
            throw error;
        }
    }

    /**
     * ✅ COMPATIBILIDAD LEGACY: Para frontend existente que usa pasos
     * 
     * @param {Array} plannedSteps - Pasos del workflow en formato legacy
     * @param {string} chatId - ID del chat
     * @returns {Promise<{missing_oauth: Array, ready_to_execute: boolean}>}
     */
    async checkOAuthRequirements(plannedSteps, chatId) {
        try {
            const response = await fetcher(`${this.oauthBaseUrl}/steps/check-requirements`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    planned_steps: plannedSteps,
                    chat_id: chatId
                })
            });

            if (!response.ok) {
                throw new Error(`OAuth requirements check failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error checking OAuth requirements:', error);
            throw error;
        }
    }

    /**
     * ✅ NUEVA API AGNÓSTICA: Lista servicios disponibles dinámicamente
     * 
     * @param {boolean} activeOnly - Solo servicios activos (default: true)
     * @returns {Promise<Object>}
     */
    async getAvailableServices(activeOnly = true) {
        try {
            const response = await fetcher(`${this.discoveryBaseUrl}/services/available?active_only=${activeOnly}`);

            if (!response.ok) {
                throw new Error(`Available services fetch failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching available services:', error);
            throw error;
        }
    }

    /**
     * ✅ NUEVA API: Lista mecanismos de auth soportados
     * 
     * @returns {Promise<Object>}
     */
    async getSupportedAuthMechanisms() {
        try {
            const response = await fetcher(`${this.discoveryBaseUrl}/mechanisms/supported`);

            if (!response.ok) {
                throw new Error(`Supported mechanisms fetch failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching supported mechanisms:', error);
            throw error;
        }
    }

    /**
     * ✅ AGNÓSTICO: Inicia OAuth usando service_id
     * 
     * @param {string} serviceId - Service ID agnóstico (ej: 'gmail', 'slack')  
     * @param {string} chatId - ID del chat
     * @returns {Promise<string>} - URL de OAuth
     */
    async initiateOAuth(serviceId, chatId) {
        try {
            const response = await fetcher(`${this.oauthBaseUrl}/initiate?service_id=${encodeURIComponent(serviceId)}&chat_id=${encodeURIComponent(chatId)}`);

            if (!response.ok) {
                throw new Error(`OAuth initiation failed: ${response.status}`);
            }

            // El endpoint retorna redirect, extraer URL
            return response.url || response.headers.get('location');
        } catch (error) {
            console.error('Error initiating OAuth:', error);
            throw error;
        }
    }

    /**
     * ✅ MEJORADO: Procesa callback OAuth 
     * 
     * @param {string} service - Servicio
     * @param {string} code - Código de autorización
     * @param {string} state - State para CSRF
     * @returns {Promise<string>} - URL de redirect
     */
    async processOAuthCallback(service, code, state) {
        try {
            const params = new URLSearchParams({
                service,
                code,
                state
            });

            const response = await fetcher(`${this.baseUrl}/callback?${params}`);

            if (!response.ok) {
                throw new Error(`OAuth callback failed: ${response.status}`);
            }

            return response.url || '/dashboard';
        } catch (error) {
            console.error('Error processing OAuth callback:', error);
            throw error;
        }
    }

    /**
     * ✅ NUEVA FUNCIÓN: Convierte workflow steps al formato esperado por la nueva API
     * 
     * @param {Array} workflowSteps - Pasos del workflow 
     * @returns {Array} - Formato para nueva API
     */
    formatStepsForUnifiedAPI(workflowSteps) {
        return workflowSteps
            .filter(step => step.default_auth) // Solo pasos que requieren auth
            .map(step => ({
                step_id: step.id || step.step_id,
                action_id: step.action_id,
                default_auth: step.default_auth,
                provider: step.default_auth?.split('_')[1], // oauth2_google -> google
                service: step.default_auth?.split('_').slice(1).join('_'), // oauth2_google_gmail -> google_gmail
                flavor: step.flavor || step.default_auth?.split('_')[2], // oauth2_google_gmail -> gmail
                scopes: step.required_scopes || [],
                metadata: {
                    step_name: step.name || step.title,
                    step_description: step.description
                }
            }));
    }

    /**
     * ✅ NUEVA FUNCIÓN: Detecta automáticamente requirements desde workflow
     * 
     * @param {Object} workflow - Objeto workflow completo
     * @returns {Promise<Object>} - OAuth requirements
     */
    async detectOAuthRequirementsFromWorkflow(workflow) {
        if (!workflow || !workflow.steps) {
            return { missing_oauth: [], ready_to_execute: true };
        }

        const formattedSteps = this.formatStepsForUnifiedAPI(workflow.steps);
        
        if (formattedSteps.length === 0) {
            return { missing_oauth: [], ready_to_execute: true };
        }

        return await this.checkOAuthRequirements(formattedSteps);
    }

    /**
     * ✅ NUEVA FUNCIÓN: Agrupa requirements por provider para mejor UX
     * 
     * @param {Array} oauthRequirements - Lista de requirements
     * @returns {Object} - Requirements agrupados por provider
     */
    groupRequirementsByProvider(oauthRequirements) {
        const grouped = {};
        
        oauthRequirements.forEach(req => {
            const provider = req.provider;
            if (!grouped[provider]) {
                grouped[provider] = {
                    provider,
                    display_name: req.display_name?.split(' ')[0] || provider,
                    requirements: [],
                    total_scopes: new Set()
                };
            }
            
            grouped[provider].requirements.push(req);
            req.scopes?.forEach(scope => grouped[provider].total_scopes.add(scope));
        });

        // Convertir Sets a Arrays
        Object.values(grouped).forEach(group => {
            group.total_scopes = Array.from(group.total_scopes);
        });

        return grouped;
    }
}

// Singleton instance
const unifiedAuthService = new UnifiedAuthService();

export default unifiedAuthService;

/**
 * Hook personalizado para usar el servicio unificado
 */
export const useUnifiedAuth = () => {
    return {
        checkOAuthRequirements: unifiedAuthService.checkOAuthRequirements.bind(unifiedAuthService),
        getAvailableAuthPolicies: unifiedAuthService.getAvailableAuthPolicies.bind(unifiedAuthService),
        initiateOAuth: unifiedAuthService.initiateOAuth.bind(unifiedAuthService),
        processOAuthCallback: unifiedAuthService.processOAuthCallback.bind(unifiedAuthService),
        formatStepsForUnifiedAPI: unifiedAuthService.formatStepsForUnifiedAPI.bind(unifiedAuthService),
        detectOAuthRequirementsFromWorkflow: unifiedAuthService.detectOAuthRequirementsFromWorkflow.bind(unifiedAuthService),
        groupRequirementsByProvider: unifiedAuthService.groupRequirementsByProvider.bind(unifiedAuthService)
    };
};