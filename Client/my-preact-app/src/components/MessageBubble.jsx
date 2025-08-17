// Componente simplificado para mostrar mensajes - testing básico
export default function MessageBubble({ message, isTemp = false }) {
  const isUser = message.role === 'user';
  
  console.log('🎨 Renderizando MessageBubble:', { 
    id: message.id, 
    role: message.role, 
    content: message.content?.substring(0, 50) + '...' 
  });

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-3xl ${isUser ? 'ml-12' : 'mr-12'}`}>
        <div className={`rounded-lg p-4 ${
          isUser 
            ? 'bg-blue-500 text-white ml-auto' 
            : 'bg-gray-100 text-gray-900'
        } ${isTemp ? 'opacity-70' : ''}`}>
          
          {/* Contenido básico */}
          <div className="text-sm font-semibold mb-1">
            {isUser ? 'Tú' : 'PerlFlow AI'}
          </div>
          
          <div className="whitespace-pre-wrap break-words">
            {message.content || '[Sin contenido]'}
          </div>
          
          {/* Debug info */}
          <div className="text-xs opacity-60 mt-2">
            ID: {message.id} | Role: {message.role}
          </div>
        </div>
      </div>
    </div>
  );
}