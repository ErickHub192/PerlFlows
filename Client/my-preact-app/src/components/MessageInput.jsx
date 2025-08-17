// Componente para input de mensajes
import { useState, useRef, useEffect, useLayoutEffect } from 'preact/hooks';

export default function MessageInput({ 
  onSendMessage, 
  disabled = false, 
  placeholder = "Escribe tu mensaje..." 
}) {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef(null);

  // ✅ DEBUG: Console log to see if this is working
  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    console.log('🔧 RESIZE DEBUG:', { 
      hasTextarea: !!textarea, 
      message: message,
      messageLength: message.length 
    });
    
    if (textarea) {
      console.log('🔧 BEFORE RESIZE:', {
        currentHeight: textarea.style.height,
        scrollHeight: textarea.scrollHeight
      });
      
      // DEV.TO implementation - PROVEN TO WORK
      textarea.style.height = "0px";
      const scrollHeight = textarea.scrollHeight;
      
      // Apply constraints (min 44px, max 200px)
      const newHeight = Math.min(Math.max(scrollHeight, 44), 200);
      textarea.style.height = newHeight + "px";
      
      console.log('🔧 AFTER RESIZE:', {
        scrollHeight: scrollHeight,
        newHeight: newHeight,
        finalHeight: textarea.style.height
      });
      
      // Handle overflow for very long content
      if (scrollHeight > 200) {
        textarea.style.overflowY = 'auto';
      } else {
        textarea.style.overflowY = 'hidden';
      }
    }
  }, [message]);

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!message.trim() || disabled || isComposing) return;
    
    const messageToSend = message.trim();
    setMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    await onSendMessage(messageToSend);
  };

  // Handle key press
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Handle input change with immediate resize
  const handleChange = (e) => {
    setMessage(e.target.value);
    
    // ✅ IMMEDIATE RESIZE: Execute right away on change
    const textarea = e.target;
    setTimeout(() => {
      textarea.style.height = "0px";
      const scrollHeight = textarea.scrollHeight;
      const newHeight = Math.min(Math.max(scrollHeight, 44), 200);
      textarea.style.height = newHeight + "px";
      textarea.style.overflowY = scrollHeight > 200 ? 'auto' : 'hidden';
    }, 0);
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 items-end">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          placeholder={placeholder}
          disabled={disabled}
          rows="1"
          className={`
            w-full p-3 pr-12 rounded-lg border border-primary/20 
            bg-surface text-text-primary placeholder-text-secondary
            resize-none transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
          style={{ 
            height: '44px',
            minHeight: '44px',
            maxHeight: '200px',
            overflowY: 'hidden',
            lineHeight: '1.5'
          }}
        />
        
        {/* Character count for long messages */}
        {message.length > 200 && (
          <div className="absolute -top-6 right-0 text-xs text-text-secondary">
            {message.length}/2000
          </div>
        )}
      </div>
      
      <button
        type="submit"
        disabled={disabled || !message.trim() || isComposing}
        className={`
          px-4 py-2 rounded-lg font-medium transition-all duration-200
          flex items-center gap-2 min-w-[100px] justify-center
          ${disabled || !message.trim() || isComposing
            ? 'bg-surface border border-primary/20 text-text-secondary cursor-not-allowed'
            : 'bg-primary text-white hover:bg-primary/90 active:scale-95'
          }
        `}
      >
        {disabled ? (
          <>
            <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full"></div>
            <span>Enviando...</span>
          </>
        ) : (
          <>
            <span>Enviar</span>
            <svg 
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2"
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22,2 15,22 11,13 2,9"></polygon>
            </svg>
          </>
        )}
      </button>
    </form>
  );
}