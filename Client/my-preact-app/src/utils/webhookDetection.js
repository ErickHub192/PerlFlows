// Client/my-preact-app/src/utils/webhookDetection.js

/**
 * 🌐 WEBHOOK DETECTION UTILITIES
 * 
 * Sistema escalable y modular para detectar diferentes tipos de webhook triggers
 * Evita hardcodear node names en el frontend
 */

// Configuración de nodos que generan webhooks
const WEBHOOK_TRIGGER_CONFIGS = {
  "Webhook": {
    actions: ["trigger"],
    generatesUrls: true,
    urlType: "generic_webhook",
    displayName: "Webhook Genérico"
  },
  "Form.webhook_trigger": {
    actions: ["webhook_trigger"],
    generatesUrls: true,
    urlType: "form_webhook", 
    displayName: "Webhook de Formulario"
  },
  "Github.webhook": {
    actions: ["webhook_trigger"],
    generatesUrls: true,
    urlType: "github_webhook",
    displayName: "Webhook de GitHub"
  },
  "Slack.webhook": {
    actions: ["webhook_trigger"],
    generatesUrls: true,
    urlType: "slack_webhook",
    displayName: "Webhook de Slack"
  },
  // Triggers internos (no generan URLs públicas)
  "Gmail.trigger": {
    actions: ["polling_trigger", "push_trigger"],
    generatesUrls: false,
    urlType: null,
    displayName: "Trigger de Gmail"
  },
  "Drive.trigger": {
    actions: ["polling_trigger", "push_trigger"],
    generatesUrls: false,
    urlType: null,
    displayName: "Trigger de Drive"
  },
  "Sheets.trigger": {
    actions: ["polling_trigger"],
    generatesUrls: false,
    urlType: null,
    displayName: "Trigger de Sheets"
  }
};

/**
 * Verifica si un step es un webhook trigger que genera URLs
 * @param {Object} step - Step del execution plan
 * @returns {boolean}
 */
export function isWebhookTrigger(step) {
  if (!step || !step.node_name) return false;
  
  const config = WEBHOOK_TRIGGER_CONFIGS[step.node_name];
  if (!config) return false;
  
  // Verificar si genera URLs
  if (!config.generatesUrls) return false;
  
  // Verificar acción específica si está definida
  if (step.action_name && config.actions.length > 0) {
    return config.actions.includes(step.action_name);
  }
  
  // Si no hay action_name específica, asumir que es válido si genera URLs
  return true;
}

/**
 * Encuentra el step de webhook en un execution plan
 * @param {Array} executionPlan - Array de steps
 * @returns {Object|null} - Webhook step o null
 */
export function findWebhookStep(executionPlan) {
  if (!Array.isArray(executionPlan)) return null;
  
  return executionPlan.find(step => isWebhookTrigger(step));
}

/**
 * Verifica si un workflow tiene webhook triggers
 * @param {Object} workflowData - Datos del workflow (lastResponse)
 * @returns {boolean}
 */
export function hasWebhookInWorkflow(workflowData) {
  if (!workflowData || !workflowData.execution_plan) return false;
  
  const webhookStep = findWebhookStep(workflowData.execution_plan);
  return !!webhookStep;
}

/**
 * Obtiene configuración de webhook para un nodo
 * @param {string} nodeName - Nombre del nodo
 * @returns {Object|null} - Configuración o null
 */
export function getWebhookConfig(nodeName) {
  return WEBHOOK_TRIGGER_CONFIGS[nodeName] || null;
}

/**
 * Genera URLs de webhook para un step
 * @param {Object} step - Step del execution plan
 * @param {string} baseUrl - URL base de la API
 * @returns {Object|null} - URLs generadas o null
 */
export function generateWebhookUrls(step, baseUrl = 'https://perlflow.com/api') {
  if (!isWebhookTrigger(step)) return null;
  
  const config = getWebhookConfig(step.node_name);
  if (!config) return null;
  
  // Usar ID del step como token único
  const token = step.id || step.action_id || 'generated-token';
  
  switch (config.urlType) {
    case 'form_webhook':
      return {
        production: `${baseUrl}/webhooks/form/${token}`,
        test: `${baseUrl}/webhooks/form/${token}?test=true`,
        documentation: `${baseUrl}/docs/webhooks/form`,
        type: 'form_webhook'
      };
      
    case 'generic_webhook':
      return {
        production: `${baseUrl}/webhooks/generic/${token}`,
        test: `${baseUrl}/webhooks/generic/${token}?test=true`, 
        documentation: `${baseUrl}/docs/webhooks/generic`,
        type: 'generic_webhook'
      };
      
    case 'github_webhook':
      return {
        production: `${baseUrl}/webhooks/github/${token}`,
        test: `${baseUrl}/webhooks/github/${token}?test=true`,
        documentation: `${baseUrl}/docs/webhooks/github`,
        type: 'github_webhook'
      };
      
    case 'slack_webhook':
      return {
        production: `${baseUrl}/webhooks/slack/${token}`,
        test: `${baseUrl}/webhooks/slack/${token}?test=true`,
        documentation: `${baseUrl}/docs/webhooks/slack`,
        type: 'slack_webhook'
      };
      
    default:
      return null;
  }
}

/**
 * Obtiene información completa de webhook para el frontend
 * @param {Object} workflowData - Datos del workflow
 * @returns {Object|null} - Info completa o null
 */
export function getWebhookInfo(workflowData) {
  const webhookStep = findWebhookStep(workflowData?.execution_plan);
  if (!webhookStep) return null;
  
  const config = getWebhookConfig(webhookStep.node_name);
  const urls = generateWebhookUrls(webhookStep);
  
  return {
    step: webhookStep,
    config: config,
    urls: urls,
    displayName: config?.displayName || webhookStep.node_name
  };
}

/**
 * Lista todos los tipos de webhook soportados
 * @returns {Array} - Array de configuraciones de webhook
 */
export function getAllWebhookTypes() {
  return Object.entries(WEBHOOK_TRIGGER_CONFIGS)
    .filter(([_, config]) => config.generatesUrls)
    .map(([nodeName, config]) => ({
      nodeName,
      ...config
    }));
}