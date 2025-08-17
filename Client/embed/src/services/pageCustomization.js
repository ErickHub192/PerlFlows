/**
 * Servicio para manejar la personalización de páginas web
 * Interactúa con la API backend para aplicar cambios visuales
 */
export class PageCustomizationService {
    constructor() {
        this.baseUrl = '/api/page-customization';
    }

    /**
     * Personaliza una página usando lenguaje natural
     * @param {string} agentId - ID del agente
     * @param {string} customizationPrompt - Descripción de los cambios deseados
     * @param {string} targetElement - Elemento específico a modificar (opcional)
     */
    async customizePage(agentId, customizationPrompt, targetElement = null) {
        try {
            const response = await fetch(`${this.baseUrl}/agents/${agentId}/customize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agent_id: agentId,
                    customization_prompt: customizationPrompt,
                    target_element: targetElement
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al personalizar la página');
            }

            return await response.json();
        } catch (error) {
            console.error('Error en customizePage:', error);
            throw error;
        }
    }

    /**
     * Obtiene el template actual de una página
     * @param {string} agentId - ID del agente
     */
    async getCurrentTemplate(agentId) {
        try {
            const response = await fetch(`${this.baseUrl}/agents/${agentId}/template`);
            
            if (!response.ok) {
                throw new Error('Error al obtener el template actual');
            }

            return await response.json();
        } catch (error) {
            console.error('Error en getCurrentTemplate:', error);
            throw error;
        }
    }

    /**
     * Genera un preview de los cambios sin aplicarlos permanentemente
     * @param {string} agentId - ID del agente
     * @param {Object} changes - Cambios a previsualizar
     */
    async previewChanges(agentId, changes) {
        try {
            const response = await fetch(`${this.baseUrl}/agents/${agentId}/preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(changes)
            });

            if (!response.ok) {
                throw new Error('Error al generar preview');
            }

            return await response.text(); // HTML content
        } catch (error) {
            console.error('Error en previewChanges:', error);
            throw error;
        }
    }

    /**
     * Aplica cambios CSS al DOM en tiempo real
     * @param {string} cssStyles - Estilos CSS a aplicar
     */
    applyStylesToDOM(cssStyles) {
        if (!cssStyles) return;

        // Buscar o crear el tag de estilos personalizados
        let styleTag = document.getElementById('custom-styles');
        
        if (!styleTag) {
            styleTag = document.createElement('style');
            styleTag.id = 'custom-styles';
            document.head.appendChild(styleTag);
        }

        // Agregar los nuevos estilos manteniendo los existentes
        const existingStyles = styleTag.textContent;
        const timestamp = new Date().toISOString();
        const newStyles = `\n\n/* Personalización aplicada el ${timestamp} */\n${cssStyles}`;
        
        styleTag.textContent = existingStyles + newStyles;

        console.log('Estilos aplicados al DOM:', cssStyles);
    }

    /**
     * Aplica modificaciones HTML al DOM
     * @param {string} htmlModifications - HTML a agregar
     */
    applyHTMLToDOM(htmlModifications) {
        if (!htmlModifications) return;

        // Crear un contenedor temporal para parsear el HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlModifications;

        // Insertar cada elemento en un lugar apropiado
        Array.from(tempDiv.children).forEach(element => {
            // Por defecto, agregar al final del body
            document.body.appendChild(element);
        });

        console.log('HTML aplicado al DOM:', htmlModifications);
    }

    /**
     * Revierte los cambios aplicados
     */
    revertChanges() {
        const styleTag = document.getElementById('custom-styles');
        if (styleTag) {
            // Mantener solo los estilos base
            const baseStyles = `
                /* Estilos base */
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                }
                
                .edit-btn {
                    transition: all 0.2s ease-in-out;
                    backdrop-filter: blur(10px);
                    background: rgba(59, 130, 246, 0.9);
                }
                
                .edit-btn:hover {
                    background: rgba(37, 99, 235, 0.9);
                    transform: translateY(-1px);
                    box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
                }
            `;
            styleTag.textContent = baseStyles;
        }
    }

    /**
     * Extrae el ID del agente de la URL actual
     */
    getAgentIdFromURL() {
        const path = window.location.pathname;
        const match = path.match(/\/embed\/([^\/]+)/);
        return match ? match[1] : null;
    }

    /**
     * Valida un prompt de personalización
     * @param {string} prompt - Prompt a validar
     */
    validateCustomizationPrompt(prompt) {
        if (!prompt || prompt.trim().length === 0) {
            return { valid: false, error: 'El prompt no puede estar vacío' };
        }

        if (prompt.length > 500) {
            return { valid: false, error: 'El prompt no puede exceder 500 caracteres' };
        }

        // Verificar que no contenga contenido potencialmente peligroso
        const dangerousPatterns = [
            /javascript:/i,
            /<script/i,
            /document\./i,
            /window\./i,
            /eval\(/i
        ];

        for (const pattern of dangerousPatterns) {
            if (pattern.test(prompt)) {
                return { valid: false, error: 'El prompt contiene contenido no permitido' };
            }
        }

        return { valid: true };
    }

    /**
     * Genera sugerencias de personalización basadas en elementos de la página
     */
    generateSuggestions() {
        const suggestions = [
            "Cambia el color de fondo a azul claro",
            "Agrega un logo en la esquina superior izquierda",
            "Cambia la fuente del texto a una más moderna",
            "Haz que los botones sean más grandes y redondos",
            "Agrega sombras a las tarjetas del chat",
            "Cambia el color del título principal",
            "Modifica el espaciado entre mensajes",
            "Agrega un degradado de color de fondo"
        ];

        // Seleccionar 3 sugerencias aleatorias
        const randomSuggestions = [];
        while (randomSuggestions.length < 3) {
            const randomIndex = Math.floor(Math.random() * suggestions.length);
            const suggestion = suggestions[randomIndex];
            if (!randomSuggestions.includes(suggestion)) {
                randomSuggestions.push(suggestion);
            }
        }

        return randomSuggestions;
    }

    /**
     * Maneja errores de la API de manera user-friendly
     * @param {Error} error - Error a manejar
     */
    handleAPIError(error) {
        console.error('API Error:', error);
        
        if (error.message.includes('Failed to fetch')) {
            return 'Error de conexión. Verifica tu conexión a internet.';
        }
        
        if (error.message.includes('404')) {
            return 'Agente no encontrado. Verifica el ID del agente.';
        }
        
        if (error.message.includes('400')) {
            return 'Los datos proporcionados no son válidos.';
        }
        
        if (error.message.includes('500')) {
            return 'Error interno del servidor. Inténtalo más tarde.';
        }
        
        return error.message || 'Error desconocido al personalizar la página';
    }
}