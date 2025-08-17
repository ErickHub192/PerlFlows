// DynamicForm.jsx
import { useState, useEffect } from 'preact/hooks';

// Custom styles for better scrolling
const customScrollStyle = `
  /* Custom scrollbar for form content */
  .smart-form-scroll {
    scrollbar-width: thin;
    scrollbar-color: rgba(139, 92, 246, 0.3) rgba(30, 41, 59, 0.1);
  }
  
  .smart-form-scroll::-webkit-scrollbar {
    width: 8px;
  }
  
  .smart-form-scroll::-webkit-scrollbar-track {
    background: rgba(30, 41, 59, 0.1);
    border-radius: 4px;
  }
  
  .smart-form-scroll::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.3);
    border-radius: 4px;
    border: 1px solid rgba(30, 41, 59, 0.1);
  }
  
  .smart-form-scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(139, 92, 246, 0.5);
  }
`;

// ✨ Helper function to convert PerlFlow AI's smart form format to JSON Schema format
function convertSmartFormToJsonSchema(smartForm) {
  const properties = {};
  const required = [];
  
  // Handle sections and fields
  if (smartForm.sections) {
    for (const section of smartForm.sections) {
      if (section.fields) {
        for (const field of section.fields) {
          const propertySchema = {
            title: field.label || field.id,
            description: field.description || field.placeholder,
            type: getJsonSchemaType(field.type)
          };
          
          // Handle specific field types
          if (field.type === 'select' && field.options) {
            propertySchema.enum = field.options.map(opt => opt.value || opt);
          }
          
          if (field.type === 'textarea') {
            propertySchema.maxLength = 1000; // Mark as long text
          }
          
          if (field.type === 'email') {
            propertySchema.format = 'email';
          }
          
          if (field.type === 'url') {
            propertySchema.format = 'uri';
          }
          
          properties[field.id] = propertySchema;
          
          if (field.required) {
            required.push(field.id);
          }
        }
      }
    }
  }
  
  return {
    title: smartForm.title || 'Formulario',
    description: smartForm.description || '',
    type: 'object',
    properties,
    required
  };
}

// Helper to map smart form field types to JSON Schema types
function getJsonSchemaType(fieldType) {
  const typeMap = {
    'text': 'string',
    'email': 'string', 
    'textarea': 'string',
    'number': 'number',
    'checkbox': 'boolean',
    'select': 'string',
    'date': 'string',
    'time': 'string',
    'url': 'string',
    'file': 'string'
  };
  
  return typeMap[fieldType] || 'string';
}

function DynamicForm({ schemaEndpoint, smartFormSchema, onSubmit, onCancel }) {
  const [schema, setSchema] = useState(null);
  const [formData, setFormData] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Inject custom styles for scrollbar
  useEffect(() => {
    const styleElement = document.createElement('style');
    styleElement.textContent = customScrollStyle;
    document.head.appendChild(styleElement);
    
    return () => {
      document.head.removeChild(styleElement);
    };
  }, []);

  useEffect(() => {
    // 🔥 NEW: Handle Smart Forms schema from window context
    if (schemaEndpoint === null && window.smartFormContext?.isSmartForm) {
      console.log("Using Smart Form schema from window context:", window.smartFormContext.formSchema);
      
      // Convert PerlFlow AI's smart form format to JSON Schema format
      const convertedSchema = convertSmartFormToJsonSchema(window.smartFormContext.formSchema);
      console.log("Converted schema:", convertedSchema);
      
      setSchema(convertedSchema);
      setIsLoading(false);
      setError(null);
      return;
    }
    
    // 🔥 NEW: Handle Smart Forms schema directly (legacy)
    if (smartFormSchema) {
      console.log("Using Smart Form schema:", smartFormSchema);
      
      // Convert PerlFlow AI's smart form format to JSON Schema format
      const convertedSchema = convertSmartFormToJsonSchema(smartFormSchema);
      console.log("Converted schema:", convertedSchema);
      
      setSchema(convertedSchema);
      setIsLoading(false);
      setError(null);
      return;
    }

    // Traditional schema fetching
    if (!schemaEndpoint) {
      setError("No schema endpoint or Smart Form schema provided");
      setIsLoading(false);
      return;
    }

    console.log("Fetching traditional schema from:", schemaEndpoint);
    async function fetchSchema() {
      try {
        setIsLoading(true);
        const response = await fetch(schemaEndpoint);
        if (!response.ok) {
          throw new Error("Error al obtener el esquema del formulario");
        }
        const data = await response.json();
        setSchema(data);
        setError(null);
      } catch (error) {
        console.error(error);
        setError(error.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchSchema();
  }, [schemaEndpoint, smartFormSchema]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? checked : value 
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      await onSubmit(formData);
    } catch (error) {
      console.error('Error submitting form:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getInputType = (property) => {
    if (property.type === 'boolean') return 'checkbox';
    if (property.type === 'integer' || property.type === 'number') return 'number';
    if (property.format === 'email') return 'email';
    if (property.format === 'uri') return 'url';
    if (property.format === 'password') return 'password';
    if (property.format === 'date') return 'date';
    if (property.format === 'time') return 'time';
    if (property.format === 'date-time') return 'datetime-local';
    return 'text';
  };

  const renderField = (key, property) => {
    const isRequired = schema.required?.includes(key);
    const inputType = getInputType(property);
    
    if (property.enum) {
      // Render select for enum values
      return (
        <select
          name={key}
          value={formData[key] || ''}
          onChange={handleChange}
          required={isRequired}
          className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all"
        >
          <option value="" disabled>
            Selecciona una opción...
          </option>
          {property.enum.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (property.type === 'boolean') {
      return (
        <div className="flex items-center">
          <input
            type="checkbox"
            name={key}
            checked={formData[key] || false}
            onChange={handleChange}
            className="w-5 h-5 text-accent bg-surface-input border-accent rounded focus:ring-accent focus:ring-2"
          />
          <span className="ml-2 text-sm text-subtle">
            {property.description || 'Marcar si es verdadero'}
          </span>
        </div>
      );
    }

    if (property.maxLength > 100 || property.type === 'string' && !property.maxLength) {
      // Render textarea for long text
      return (
        <textarea
          name={key}
          value={formData[key] || ''}
          onChange={handleChange}
          required={isRequired}
          placeholder={property.description || `Ingresa ${property.title || key}`}
          className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all resize-none"
          rows={3}
          maxLength={property.maxLength}
        />
      );
    }

    return (
      <input
        type={inputType}
        name={key}
        value={formData[key] || ''}
        onChange={handleChange}
        required={isRequired}
        placeholder={property.description || `Ingresa ${property.title || key}`}
        min={property.minimum}
        max={property.maximum}
        maxLength={property.maxLength}
        className="w-full surface-input rounded-xl px-4 py-3 focus-elegant bg-transparent text-elegant placeholder-text-muted transition-all"
      />
    );
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-gradient-main/80 backdrop-blur-sm z-50">
        <div className="glass-card p-8 shadow-elegant-lg">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            <span className="ml-3 text-subtle">Cargando formulario...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-gradient-main/80 backdrop-blur-sm z-50">
        <div className="glass-card p-6 shadow-elegant-lg max-w-md w-full mx-4">
          <div className="text-center">
            <div className="text-red-500 text-xl mb-2">⚠️</div>
            <h3 className="text-lg font-semibold text-elegant mb-2">Error</h3>
            <p className="text-subtle mb-4">{error}</p>
            <button
              onClick={onCancel}
              className="btn-secondary px-4 py-2 rounded-lg transition-colors"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gradient-main/80 backdrop-blur-sm z-50">
      <div className="glass-card rounded-xl shadow-elegant-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <form onSubmit={handleSubmit} className="flex flex-col h-full min-h-0">
          {/* Header */}
          <div className="px-6 py-4 border-b border-primary">
            <h3 className="text-xl font-semibold text-elegant">
              {schema.title || 'Formulario Dinámico'}
            </h3>
            {schema.description && (
              <p className="text-sm text-subtle mt-1">{schema.description}</p>
            )}
          </div>

          {/* Form Content - Scrollable Area */}
          <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0 smart-form-scroll">
            <div className="space-y-6 pb-4">
              {Object.keys(schema.properties).map((key) => {
                const property = schema.properties[key];
                const isRequired = schema.required?.includes(key);
                
                return (
                  <div key={key} className="space-y-2">
                    <label className="block text-sm font-medium text-elegant">
                      {property.title || key}
                      {isRequired && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    {renderField(key, property)}
                    {property.description && property.type !== 'boolean' && (
                      <p className="text-xs text-muted">{property.description}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-primary surface-elevated">
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={onCancel}
                disabled={isSubmitting}
                className="btn-glass px-4 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary px-6 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
              >
                {isSubmitting && (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                )}
                {isSubmitting ? 'Enviando...' : 'Enviar'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default DynamicForm;