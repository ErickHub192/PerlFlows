// src/stores/llmStore.js
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { llmApi } from '../api/llm';

export const useLLMStore = create(
  persist(
    (set, get) => ({
      // State
      providers: [],
      models: [],
      selectedModel: null,
      selectedProvider: null,
      recommendedModels: [],
      loading: false,
      error: null,
      initialized: false,
      
      // Health status
      providersHealth: {},
      lastHealthCheck: null,

      // Actions
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),

      /**
       * Initialize the store with providers and models data
       */
      initialize: async () => {
        if (get().initialized) return;
        
        try {
          set({ loading: true, error: null });
          
          // Load providers with models
          const providers = await llmApi.getProviders();
          
          // Extract all models from providers
          const allModels = providers.reduce((acc, provider) => {
            const providerModels = (provider.models || []).map(model => ({
              ...model,
              provider_name: provider.name,
              provider_key: provider.provider_key
            }));
            return [...acc, ...providerModels];
          }, []);
          
          console.log('🔍 LLM Store - providers loaded:', providers.length);
          console.log('🔍 LLM Store - total models:', allModels.length);
          console.log('🔍 LLM Store - sample model:', allModels[0]);
          
          // Set default model (first active or first available)
          const defaultModel = allModels.find(m => m.is_active) || allModels[0];
          
          const defaultProvider = providers.find(p => 
            p.provider_key === defaultModel?.provider_key
          );

          set({
            providers,
            models: allModels,
            recommendedModels: [],
            selectedModel: defaultModel,
            selectedProvider: defaultProvider,
            initialized: true,
            loading: false
          });
          
        } catch (error) {
          console.error('Failed to initialize LLM store:', error);
          set({ 
            error: error.message || 'Failed to load models',
            loading: false 
          });
        }
      },

      /**
       * Refresh providers and models data
       */
      refresh: async () => {
        set({ initialized: false });
        await get().initialize();
      },

      /**
       * Select a specific model
       */
      selectModel: (model) => {
        const provider = get().providers.find(p => 
          p.provider_key === model.provider_key
        );
        
        set({ 
          selectedModel: model,
          selectedProvider: provider
        });
      },

      /**
       * Select model by key
       */
      selectModelByKey: (modelKey) => {
        const model = get().models.find(m => m.model_key === modelKey);
        if (model) {
          get().selectModel(model);
        }
      },

      /**
       * Get models for a specific provider
       */
      getModelsByProvider: (providerKey) => {
        return get().models.filter(m => m.provider_key === providerKey);
      },

      /**
       * Get active models only
       */
      getActiveModels: () => {
        return get().models.filter(m => m.is_active);
      },

      /**
       * Search models by name or description
       */
      searchModels: async (query) => {
        try {
          set({ loading: true, error: null });
          
          const results = await llmApi.searchModels(query);
          
          set({ loading: false });
          return results;
          
        } catch (error) {
          console.error('Failed to search models:', error);
          set({ 
            error: error.message || 'Search failed',
            loading: false 
          });
          return [];
        }
      },

      /**
       * Check providers health
       */
      checkHealth: async () => {
        try {
          const healthData = await llmApi.checkProvidersHealth();
          
          set({
            providersHealth: healthData.providers,
            lastHealthCheck: new Date().toISOString()
          });
          
          return healthData;
          
        } catch (error) {
          console.error('Failed to check providers health:', error);
          set({ error: error.message || 'Health check failed' });
          return null;
        }
      },


      /**
       * Get models with filters
       */
      getModelsWithFilters: async (filters = {}) => {
        try {
          set({ loading: true, error: null });
          
          const filteredModels = await llmApi.getModels(filters);
          
          set({ loading: false });
          return filteredModels;
          
        } catch (error) {
          console.error('Failed to get filtered models:', error);
          set({ 
            error: error.message || 'Failed to filter models',
            loading: false 
          });
          return [];
        }
      },

      /**
       * Clear error state
       */
      clearError: () => set({ error: null }),

      /**
       * Reset store to initial state
       */
      reset: () => set({
        providers: [],
        models: [],
        selectedModel: null,
        selectedProvider: null,
        recommendedModels: [],
        loading: false,
        error: null,
        initialized: false,
        providersHealth: {},
        lastHealthCheck: null
      })
    }),
    {
      name: 'llm-store',
      partialize: (state) => ({
        selectedModel: state.selectedModel,
        selectedProvider: state.selectedProvider,
        // Don't persist providers/models as they should be fresh on reload
      }),
    }
  )
);