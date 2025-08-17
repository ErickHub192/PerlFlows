// src/components/ModelSelector.jsx
import { useState, useEffect, useRef } from 'preact/hooks';
import { useLLMStore } from '../stores/llmStore';

export default function ModelSelector({ className = "", showProvider = true, compact = false, onModelChange = null }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);
  
  const {
    providers,
    models,
    selectedModel,
    loading,
    error,
    initialized,
    initialize,
    selectModel,
    clearError,
    getActiveModels
  } = useLLMStore();

  // Initialize store on mount
  useEffect(() => {
    if (!initialized) {
      initialize();
    }
  }, [initialized, initialize]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get filtered models based on search
  const getFilteredModels = () => {
    const activeModels = getActiveModels();
    
    if (!searchTerm.trim()) {
      return activeModels;
    }
    
    return activeModels.filter(model => 
      model.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      model.model_key?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (model.provider_name && model.provider_name.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  };

  // Group models by provider
  const getGroupedModels = () => {
    const filteredModels = getFilteredModels();
    const grouped = {};
    
    filteredModels.forEach(model => {
      const providerKey = model.provider_key;
      if (!grouped[providerKey]) {
        const provider = providers.find(p => p.provider_key === providerKey);
        grouped[providerKey] = {
          provider: provider || { name: providerKey, provider_key: providerKey },
          models: []
        };
      }
      grouped[providerKey].models.push(model);
    });
    
    return grouped;
  };

  const handleModelSelect = (model) => {
    selectModel(model);
    setIsOpen(false);
    setSearchTerm('');
    
    // Notify parent component of model change
    if (onModelChange) {
      onModelChange(model);
    }
  };

  const formatCost = (cost) => {
    if (!cost || isNaN(cost)) return 'N/A';
    if (cost < 0.001) return '<$0.001';
    return `$${cost.toFixed(3)}`;
  };

  const formatContextLength = (length) => {
    if (!length || isNaN(length)) return 'N/A';
    if (length >= 1000000) return `${(length / 1000000).toFixed(1)}M`;
    if (length >= 1000) return `${(length / 1000).toFixed(0)}K`;
    return length.toString();
  };

  if (loading && !initialized) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="animate-spin w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full"></div>
        <span className="text-sm text-gray-400">Loading models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="text-red-400 text-sm">
          Error: {error}
          <button 
            onClick={clearError}
            className="ml-2 text-xs underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!selectedModel) {
    return (
      <div className={`text-gray-400 text-sm ${className}`}>
        No model selected
      </div>
    );
  }

  const groupedModels = getGroupedModels();

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Selected Model Display */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          flex items-center justify-between w-full px-3 py-2 
          bg-gray-800 hover:bg-gray-700 border border-gray-600 
          rounded-lg transition-colors focus:outline-none focus:ring-2 
          focus:ring-purple-500 focus:border-transparent
          ${compact ? 'text-sm' : ''}
        `}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Model Icon/Badge */}
          <div className={`
            flex-shrink-0 w-2 h-2 rounded-full
            ${selectedModel.is_recommended ? 'bg-green-400' : 'bg-gray-400'}
          `} />
          
          <div className="min-w-0 flex-1 text-left">
            <div className="text-white font-medium truncate">
              {selectedModel.name}
            </div>
            {!compact && showProvider && (
              <div className="text-xs text-gray-400 truncate">
                {selectedModel.provider_name} • {formatContextLength(selectedModel.context_length)} tokens
              </div>
            )}
          </div>
        </div>
        
        {/* Cost Display */}
        {!compact && (
          <div className="text-xs text-gray-400 ml-2">
            {formatCost(selectedModel.cost_per_1k_input_tokens || selectedModel.input_cost_per_1k)}/1K
          </div>
        )}
        
        {/* Dropdown Arrow */}
        <svg 
          className={`w-4 h-4 ml-2 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 max-h-96 overflow-hidden">
          {/* Search Box */}
          <div className="p-3 border-b border-gray-600">
            <input
              type="text"
              placeholder="Search models..."
              value={searchTerm}
              onInput={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>


          {/* Models by Provider */}
          <div className="max-h-64 overflow-y-auto">
            {Object.entries(groupedModels).map(([providerKey, { provider, models: providerModels }]) => (
              <div key={providerKey}>
                {/* Provider Header */}
                <div className="px-3 py-2 text-xs font-medium text-gray-400 bg-gray-750 sticky top-0">
                  {provider.name}
                  <span className="ml-2 text-gray-500">({providerModels.length})</span>
                </div>
                
                {/* Provider Models */}
                {providerModels.map((model) => (
                  <ModelOption
                    key={model.id}
                    model={model}
                    isSelected={selectedModel?.id === model.id}
                    onClick={() => handleModelSelect(model)}
                    showProvider={false} // Don't show provider name when grouped
                    compact={compact}
                  />
                ))}
              </div>
            ))}
          </div>

          {/* No Results */}
          {Object.keys(groupedModels).length === 0 && (
            <div className="px-3 py-4 text-center text-gray-400">
              No models found matching "{searchTerm}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Individual Model Option Component
function ModelOption({ model, isSelected, onClick, showProvider, compact }) {
  const formatCost = (cost) => {
    if (!cost || isNaN(cost)) return 'N/A';
    if (cost < 0.001) return '<$0.001';
    return `$${cost.toFixed(3)}`;
  };

  const formatContextLength = (length) => {
    if (!length || isNaN(length)) return 'N/A';
    if (length >= 1000000) return `${(length / 1000000).toFixed(1)}M`;
    if (length >= 1000) return `${(length / 1000).toFixed(0)}K`;
    return length.toString();
  };

  return (
    <button
      onClick={onClick}
      className={`
        w-full px-3 py-2 text-left hover:bg-gray-700 transition-colors
        ${isSelected ? 'bg-purple-900/50 border-r-2 border-purple-500' : ''}
        ${compact ? 'py-1' : ''}
      `}
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {/* Status indicators */}
            <div className={`
              w-2 h-2 rounded-full flex-shrink-0
              ${model.is_recommended ? 'bg-green-400' : 'bg-gray-500'}
            `} />
            
            <span className="text-white font-medium truncate">
              {model.name}
            </span>
            
            {model.is_recommended && (
              <span className="text-xs bg-green-600 text-white px-1 py-0.5 rounded">
                REC
              </span>
            )}
          </div>
          
          {!compact && (
            <div className="text-xs text-gray-400 mt-1 flex items-center gap-2">
              {showProvider && model.provider_name && (
                <span>{model.provider_name}</span>
              )}
              <span>{formatContextLength(model.context_length)} tokens</span>
              {model.capabilities && model.capabilities.length > 0 && (
                <span>• {model.capabilities.slice(0, 2).join(', ')}</span>
              )}
            </div>
          )}
        </div>
        
        <div className="text-xs text-gray-400 ml-2 flex-shrink-0">
          {formatCost(model.cost_per_1k_input_tokens || model.input_cost_per_1k)}/1K
        </div>
      </div>
    </button>
  );
}