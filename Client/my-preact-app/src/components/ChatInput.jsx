// src/components/ChatInput.jsx

import { useState, useRef, useEffect } from 'preact/hooks';

export default function ChatInput({ onSendMessage, disabled = false, placeholder = "Escribe tu mensaje..." }) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // ✅ ChatGPT/Claude exact technique from CSS-Tricks
  const handleInputChange = (e) => {
    setMessage(e.target.value);
  };

  const handleInput = (e) => {
    const textarea = e.target;
    // CSS-Tricks exact implementation
    textarea.style.height = 'auto';
    
    // Calculate height with constraints
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 44), 200);
    textarea.style.height = newHeight + 'px';
    
    // Show scroll if needed
    if (textarea.scrollHeight > 200) {
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.overflowY = 'hidden';
    }
  };

  // Reset height when message is cleared
  useEffect(() => {
    if (message === '' && textareaRef.current) {
      textareaRef.current.style.height = '44px';
      textareaRef.current.style.overflowY = 'hidden';
    }
  }, [message]);

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t">
      <textarea
        ref={textareaRef}
        value={message}
        onChange={handleInputChange}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 p-3 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        rows={1}
        style={{ 
          height: '44px',
          minHeight: '44px',
          maxHeight: '200px',
          lineHeight: '1.5',
          overflowY: 'hidden',
          resize: 'none' // Ensure no manual resize
        }}
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end"
      >
        Enviar
      </button>
    </form>
  );
}