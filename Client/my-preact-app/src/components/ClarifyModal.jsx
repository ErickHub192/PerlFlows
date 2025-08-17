import { useState } from 'preact/hooks';

const ClarifyModal = ({ questions, onSubmit, onCancel }) => {
  const [answers, setAnswers] = useState({});

  const handleInputChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(answers);
  };

  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4 max-h-[80vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">
          Aclaración Requerida
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {questions.map((question, index) => (
            <div key={question.id || index} className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                {question.question || question.text || question}
              </label>
              
              {question.type === 'select' && question.options ? (
                <select
                  value={answers[question.id || index] || ''}
                  onChange={(e) => handleInputChange(question.id || index, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Seleccionar...</option>
                  {question.options.map((option, optIndex) => (
                    <option key={optIndex} value={option.value || option}>
                      {option.label || option}
                    </option>
                  ))}
                </select>
              ) : question.type === 'textarea' ? (
                <textarea
                  value={answers[question.id || index] || ''}
                  onChange={(e) => handleInputChange(question.id || index, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows="3"
                  placeholder={question.placeholder || 'Ingresa tu respuesta...'}
                  required
                />
              ) : (
                <input
                  type={question.type || 'text'}
                  value={answers[question.id || index] || ''}
                  onChange={(e) => handleInputChange(question.id || index, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={question.placeholder || 'Ingresa tu respuesta...'}
                  required
                />
              )}
              
              {question.description && (
                <p className="text-xs text-gray-500">{question.description}</p>
              )}
            </div>
          ))}
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              Enviar Respuestas
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClarifyModal;