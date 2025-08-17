// src/components/ServiceSelection.jsx

import { useState } from 'preact/hooks';

export default function ServiceSelection({ 
  suggestions = [], 
  onSelect, 
  onClose, 
  isVisible = false 
}) {
  const [selectedServices, setSelectedServices] = useState([]);

  if (!isVisible) return null;

  const handleToggleService = (service) => {
    setSelectedServices(prev => {
      const isSelected = prev.some(s => s.node_id === service.node_id && s.action_id === service.action_id);
      if (isSelected) {
        return prev.filter(s => !(s.node_id === service.node_id && s.action_id === service.action_id));
      } else {
        return [...prev, service];
      }
    });
  };

  const handleConfirm = () => {
    onSelect(selectedServices);
    setSelectedServices([]);
  };

  const handleCancel = () => {
    setSelectedServices([]);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-hidden border border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-white">Seleccionar Servicios</h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="mb-4 text-sm text-gray-300">
          Selecciona los servicios que quieres usar para tu workflow:
        </div>

        <div className="max-h-[400px] overflow-y-auto space-y-2 mb-6">
          {suggestions.map((service, index) => {
            const isSelected = selectedServices.some(
              s => s.node_id === service.node_id && s.action_id === service.action_id
            );
            
            return (
              <div
                key={`${service.node_id}-${service.action_id}-${index}`}
                className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                  isSelected
                    ? 'border-blue-400 bg-blue-900/30'
                    : 'border-gray-600 hover:border-gray-500 bg-gray-800'
                }`}
                onClick={() => handleToggleService(service)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-white">{service.node_name}</div>
                    <div className="text-sm text-gray-300">{service.action_name}</div>
                    {service.description && (
                      <div className="text-xs text-gray-400 mt-1">{service.description}</div>
                    )}
                  </div>
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    isSelected
                      ? 'border-blue-400 bg-blue-500 text-white'
                      : 'border-gray-500'
                  }`}>
                    {isSelected && '✓'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={selectedServices.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Continuar ({selectedServices.length})
          </button>
        </div>
      </div>
    </div>
  );
}