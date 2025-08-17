import { h, render } from 'https://unpkg.com/preact@10.15.1?module';
import { useState, useEffect } from 'https://unpkg.com/preact@10.15.1/hooks/dist/hooks.module.js?module';
import { PageCustomizationService } from './services/pageCustomization.js';

// Inicializar servicio de personalización
const customizationService = new PageCustomizationService();

function ChatInterface({ token }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const send = async () => {
    if (!text.trim() || isLoading) return;

    const agentId = customizationService.getAgentIdFromURL();
    if (!agentId) {
      console.error('No se pudo obtener el ID del agente de la URL');
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`/api/ai_agents/${agentId}/run`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'X-API-Key': token || ''
        },
        body: JSON.stringify({ 
          prompt: text,
          temperature: 0.7
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages([...messages, 
          { role: 'user', content: text }, 
          { role: 'assistant', content: data.final_output || data.reply || 'Sin respuesta' }
        ]);
        setText('');
      } else {
        const errorData = await res.json();
        console.error('Error en la respuesta del chat:', errorData);
        setMessages([...messages, 
          { role: 'user', content: text }, 
          { role: 'assistant', content: `Error: ${errorData.detail || 'Error del servidor'}` }
        ]);
        setText('');
      }
    } catch (error) {
      console.error('Error al enviar mensaje:', error);
      setMessages([...messages, 
        { role: 'user', content: text }, 
        { role: 'assistant', content: 'Error de conexión. Inténtalo de nuevo.' }
      ]);
      setText('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return h('div', { class: 'flex flex-col h-full' }, [
    // Área de mensajes
    h('div', { 
      class: 'flex-1 overflow-y-auto space-y-3 mb-4 p-2',
      id: 'messages-area'
    }, messages.map((m, index) => 
      h('div', { 
        key: index,
        class: `message ${m.role} p-3 rounded-lg max-w-xs ${
          m.role === 'user' 
            ? 'ml-auto bg-blue-500 text-white' 
            : 'mr-auto bg-gray-100 text-gray-800'
        }`
      }, m.content)
    )),
    
    // Área de input
    h('div', { class: 'flex space-x-2 items-end' }, [
      h('textarea', {
        class: 'flex-1 border border-gray-300 rounded-lg px-3 py-2 resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        value: text,
        placeholder: 'Escribe tu mensaje aquí...',
        rows: 2,
        onInput: e => setText(e.target.value),
        onKeyPress: handleKeyPress,
        disabled: isLoading
      }),
      h('button', {
        class: `px-4 py-2 rounded-lg font-medium transition-colors ${
          isLoading || !text.trim()
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-500 text-white hover:bg-blue-600'
        }`,
        onClick: send,
        disabled: isLoading || !text.trim()
      }, isLoading ? 'Enviando...' : 'Enviar')
    ])
  ]);
}

function EditModal({ isOpen, onClose, agentId }) {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  const clearMessage = () => setMessage({ text: '', type: '' });

  const showMessage = (text, type = 'info') => {
    setMessage({ text, type });
    setTimeout(clearMessage, 5000);
  };

  const handleSubmit = async () => {
    const validation = customizationService.validateCustomizationPrompt(prompt);
    if (!validation.valid) {
      showMessage(validation.error, 'error');
      return;
    }

    setIsLoading(true);
    clearMessage();

    try {
      const result = await customizationService.customizePage(agentId, prompt);
      
      if (result.success) {
        // Aplicar cambios al DOM
        customizationService.applyStylesToDOM(result.css_styles);
        if (result.html_modifications) {
          customizationService.applyHTMLToDOM(result.html_modifications);
        }
        
        showMessage(
          `✅ Cambios aplicados: ${result.applied_changes.join(', ')}`, 
          'success'
        );
        
        // Cerrar modal después de 2 segundos
        setTimeout(() => {
          onClose();
          setPrompt('');
          clearMessage();
        }, 2000);
      } else {
        showMessage(`❌ Error: ${result.error_message}`, 'error');
      }
    } catch (error) {
      const errorMessage = customizationService.handleAPIError(error);
      showMessage(`❌ ${errorMessage}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    onClose();
    setPrompt('');
    clearMessage();
  };

  if (!isOpen) return null;

  return h('div', { 
    class: 'fixed inset-0 modal-backdrop z-40',
    onClick: (e) => e.target === e.currentTarget && handleCancel()
  }, [
    h('div', { class: 'flex items-center justify-center min-h-screen p-4' }, [
      h('div', { class: 'modal-content w-full max-w-2xl p-6' }, [
        // Header
        h('div', { class: 'flex justify-between items-center mb-6' }, [
          h('h2', { class: 'text-2xl font-bold text-gray-800' }, 'Personalizar Página'),
          h('button', {
            class: 'text-gray-500 hover:text-gray-700 text-2xl font-bold',
            onClick: handleCancel
          }, '×')
        ]),
        
        // Content
        h('div', { class: 'mb-6' }, [
          h('p', { class: 'text-gray-600 mb-4' }, 
            'Describe cómo quieres personalizar esta página usando lenguaje natural:'
          ),
          h('textarea', {
            class: 'w-full h-32 p-4 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            value: prompt,
            placeholder: "Ejemplo: 'Cambia el color de fondo a azul claro y agrega un logo en la esquina superior izquierda'",
            onInput: e => setPrompt(e.target.value),
            disabled: isLoading
          })
        ]),
        
        // Actions
        h('div', { class: 'flex justify-between items-center' }, [
          h('div', { class: 'text-sm text-gray-500' }, [
            h('span', { class: 'font-medium' }, 'Ejemplos: '),
            'cambiar colores, agregar logos, modificar fuentes, ajustar espaciado'
          ]),
          h('div', { class: 'flex space-x-3' }, [
            h('button', {
              class: 'px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50',
              onClick: handleCancel,
              disabled: isLoading
            }, 'Cancelar'),
            h('button', {
              class: `px-6 py-2 rounded-lg font-medium ${
                isLoading || !prompt.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`,
              onClick: handleSubmit,
              disabled: isLoading || !prompt.trim()
            }, isLoading ? 'Aplicando...' : 'Aplicar Cambios')
          ])
        ]),
        
        // Loading State
        isLoading && h('div', { class: 'mt-4 p-4 bg-blue-50 rounded-lg' }, [
          h('div', { class: 'flex items-center space-x-3' }, [
            h('div', { class: 'animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500' }),
            h('span', { class: 'text-blue-700' }, 'Generando personalización...')
          ])
        ]),
        
        // Messages
        message.text && h('div', { 
          class: `mt-4 p-4 rounded-lg ${
            message.type === 'success' ? 'bg-green-50 text-green-700' :
            message.type === 'error' ? 'bg-red-50 text-red-700' :
            'bg-blue-50 text-blue-700'
          }`
        }, message.text)
      ])
    ])
  ]);
}

function App() {
  const params = new URLSearchParams(location.search);
  const token = params.get('token');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const agentId = customizationService.getAgentIdFromURL();

  useEffect(() => {
    // Configurar event listeners para los botones del DOM
    const editBtn = document.getElementById('edit-page-btn');
    if (editBtn) {
      editBtn.addEventListener('click', () => setIsEditModalOpen(true));
    }

    // Cleanup
    return () => {
      if (editBtn) {
        editBtn.removeEventListener('click', () => setIsEditModalOpen(true));
      }
    };
  }, []);

  // Renderizar la interfaz de chat en el contenedor específico
  const chatContainer = document.getElementById('chat-container');
  if (chatContainer) {
    render(h(ChatInterface, { token }), chatContainer);
  }

  // Renderizar el modal de edición
  return h(EditModal, {
    isOpen: isEditModalOpen,
    onClose: () => setIsEditModalOpen(false),
    agentId: agentId
  });
}

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', () => {
  // Renderizar la aplicación principal
  const appContainer = document.getElementById('app');
  if (appContainer) {
    render(h(App), appContainer);
  }
  
  console.log('🚀 Aplicación de personalización de páginas iniciada');
  console.log('🎨 Servicio de personalización disponible');
});
