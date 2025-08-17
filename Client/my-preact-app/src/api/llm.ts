// src/api/llm.ts
import { fetcher } from './fetcher';

export interface LLMProvider {
  id: string;
  provider_key: string;
  name: string;
  description: string;
  is_active: boolean;
  health_check_url?: string;
  rate_limit_rpm?: number;
  api_base_url?: string;
  models: LLMModel[];
  model_count: number;
  recommended_model_count: number;
  default_model_key?: string;
}

export interface LLMModel {
  id: string;
  model_key: string;
  name: string;
  description: string;
  provider_key: string;
  provider_name?: string;
  context_length: number;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  capabilities: string[];
  is_recommended: boolean;
  is_active: boolean;
  performance_score?: number;
  created_at: string;
  updated_at: string;
}

export interface ModelFilters {
  provider_key?: string;
  capabilities?: string[];
  min_context_length?: number;
  max_cost_per_1k_input?: number;
  include_inactive?: boolean;
}


export interface UsageAnalytics {
  summary: {
    total_requests: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost: number;
    average_response_time_ms: number;
  };
  daily_trend: Array<{
    date: string;
    requests: number;
    cost: number;
    tokens: number;
  }>;
  period_days: number;
  provider_filter?: string;
}

export interface ProviderHealth {
  [provider_key: string]: {
    healthy: boolean;
    status_code?: number;
    response_time_ms?: number;
    error?: string;
    last_checked: string;
  };
}

class LLMApi {
  /**
   * Get all LLM providers with their models
   */
  async getProviders(includeInactive = false): Promise<LLMProvider[]> {
    const params = new URLSearchParams();
    if (includeInactive) params.append('include_inactive', 'true');
    
    return fetcher(`/api/llm/providers?${params.toString()}`);
  }

  /**
   * Get specific provider with detailed model information
   */
  async getProvider(providerKey: string): Promise<LLMProvider> {
    return fetcher(`/api/llm/providers/${providerKey}`);
  }

  /**
   * Get models for a specific provider
   */
  async getProviderModels(providerKey: string, includeInactive = false): Promise<LLMModel[]> {
    const params = new URLSearchParams();
    if (includeInactive) params.append('include_inactive', 'true');
    
    return fetcher(`/api/llm/providers/${providerKey}/models?${params.toString()}`);
  }

  /**
   * Get all available models with filtering
   */
  async getModels(filters: ModelFilters = {}): Promise<LLMModel[]> {
    const params = new URLSearchParams();
    
    if (filters.provider_key) params.append('provider_key', filters.provider_key);
    if (filters.capabilities) {
      filters.capabilities.forEach(cap => params.append('capabilities', cap));
    }
    if (filters.min_context_length) params.append('min_context_length', filters.min_context_length.toString());
    if (filters.max_cost_per_1k_input) params.append('max_cost_per_1k_input', filters.max_cost_per_1k_input.toString());
    if (filters.include_inactive) params.append('include_inactive', 'true');
    
    return fetcher(`/api/llm/models?${params.toString()}`);
  }


  /**
   * Search models by name, description, or capabilities
   */
  async searchModels(query: string, limit = 20): Promise<LLMModel[]> {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString()
    });
    
    return fetcher(`/api/llm/models/search?${params.toString()}`);
  }

  /**
   * Get specific model details
   */
  async getModel(modelId: string): Promise<LLMModel> {
    return fetcher(`/api/llm/models/${modelId}`);
  }

  /**
   * Check health status of all providers
   */
  async checkProvidersHealth(): Promise<{
    status: string;
    providers: ProviderHealth;
    healthy_count: number;
    total_count: number;
  }> {
    return fetcher('/api/llm/health');
  }

  /**
   * Get usage analytics for the current user
   */
  async getUserAnalytics(days = 30, providerKey?: string): Promise<UsageAnalytics> {
    const params = new URLSearchParams({
      days: days.toString()
    });
    
    if (providerKey) params.append('provider_key', providerKey);
    
    return fetcher(`/api/llm/usage/analytics?${params.toString()}`);
  }
}

export const llmApi = new LLMApi();

// Chat with custom model
export interface ChatWithModelRequest {
  session_id: string;
  message: string;
  conversation?: Array<{role: string, content: string}>;
  model_key?: string;
}

export interface ChatResponse {
  reply: string;
  conversation: Array<{role: string, content: string}>;
  finalize: boolean;
  metadata?: any;
}

export async function chatWithCustomModel(request: ChatWithModelRequest): Promise<ChatResponse> {
  const params = new URLSearchParams();
  if (request.model_key) {
    params.append('model_key', request.model_key);
  }
  
  const url = `/api/chat/with-model${params.toString() ? '?' + params.toString() : ''}`;
  
  return fetcher(url, {
    method: 'POST',
    body: {
      session_id: request.session_id,
      message: request.message,
      conversation: request.conversation || []
    }
  });
}