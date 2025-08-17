# 🎨 Personalización de Páginas Web con Lenguaje Natural

## 📋 Descripción General

Esta funcionalidad permite a los usuarios personalizar sus páginas web deployadas usando comandos en lenguaje natural. Los usuarios pueden modificar aspectos visuales como colores, fuentes, espaciado y agregar elementos decorativos sin necesidad de conocimiento técnico.

## 🏗️ Arquitectura

### **Separación de Responsabilidades**

```
┌─────────────────────────────────────────────────────────────┐
│                    PÁGINA WEB DEPLOYADA                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   BOTÓN EDITAR  │    │       CHAT PRINCIPAL            │ │
│  │  (Esquina Sup.) │    │    (Agente Deployado)          │ │
│  └─────────────────┘    └─────────────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              MODAL DE EDICIÓN                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │     Input: "Cambia el color a azul..."              │ │ │
│  │  │     Powered by: AGENTE MODIFICADOR                  │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### **Componentes Backend**

- **Handler**: `WebPageModifierHandler` - Agente especializado en modificaciones web
- **Service**: `PageCustomizationService` - Lógica de negocio y coordinación
- **Router**: `PageCustomizationRouter` - Endpoints REST API
- **DTOs**: Transferencia de datos estructurada

### **Componentes Frontend**

- **HTML**: Página embed actualizada con botón de edición y modal
- **JavaScript**: Servicio y componentes para interfaz de personalización
- **CSS**: Estilos responsivos y animaciones

## 🚀 Funcionalidades

### **1. Botón de Edición**
- Ubicado en esquina superior derecha
- Acceso directo a personalización
- No interfiere con chat principal

### **2. Modal de Personalización**
- Interface intuitiva para prompts
- Validación en tiempo real
- Estados de carga y mensajes de resultado

### **3. Agente Modificador**
- Especializado en cambios visuales únicos
- Validación de seguridad integrada
- Generación de CSS/HTML seguro

### **4. Aplicación en Tiempo Real**
- Cambios aplicados inmediatamente
- Preview antes de confirmar
- Persistencia automática

## 📝 Ejemplos de Uso

### **Prompts Soportados**

```
✅ "Cambia el color de fondo a azul claro"
✅ "Agrega un logo en la esquina superior izquierda"  
✅ "Cambia la fuente del texto a una más moderna"
✅ "Haz que los botones sean más grandes y redondos"
✅ "Agrega sombras a las tarjetas del chat"
✅ "Modifica el espaciado entre mensajes"
```

### **Resultado Esperado**

```css
/* Ejemplo de CSS generado */
body {
    background-color: #e3f2fd;
    font-family: 'Inter', sans-serif;
}

.message {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem;
}

button {
    border-radius: 12px;
    padding: 12px 24px;
}
```

## 🔧 API Endpoints

### **POST** `/api/page-customization/agents/{agent_id}/customize`

Personaliza una página usando lenguaje natural.

**Request Body:**
```json
{
  "agent_id": "agent_123",
  "customization_prompt": "Cambia el color de fondo a azul claro",
  "target_element": "body"
}
```

**Response:**
```json
{
  "success": true,
  "applied_changes": ["Cambió color de fondo a #e3f2fd"],
  "css_styles": "body { background-color: #e3f2fd; }",
  "preview_url": "/embed/agent_123?preview=true"
}
```

### **GET** `/api/page-customization/agents/{agent_id}/template`

Obtiene el template actual de una página.

**Response:**
```json
{
  "template_id": "template_456",
  "agent_id": "agent_123", 
  "html_content": "<!DOCTYPE html>...",
  "css_styles": "body { ... }",
  "is_active": true
}
```

### **POST** `/api/page-customization/agents/{agent_id}/preview`

Genera preview de cambios sin aplicarlos permanentemente.

### **GET** `/api/page-customization/agents/{agent_id}/template/history`

Obtiene historial de templates para rollback.

### **POST** `/api/page-customization/agents/{agent_id}/template/rollback/{template_id}`

Revierte a una versión anterior del template.

## 🔒 Seguridad

### **Validaciones Implementadas**

1. **CSS Safety**: Lista blanca de propiedades CSS permitidas
2. **HTML Sanitization**: Prevención de injection de scripts
3. **Pattern Detection**: Detección de patrones peligrosos
4. **Input Validation**: Longitud y contenido de prompts

### **Propiedades CSS Permitidas**

```python
allowed_css_properties = {
    'background-color', 'color', 'font-family', 'font-size', 
    'font-weight', 'margin', 'padding', 'border', 
    'border-radius', 'width', 'height', 'display', 
    'position', 'opacity', 'box-shadow', 'text-align'
}
```

### **Patrones Bloqueados**

- `javascript:` URLs
- `<script>` tags
- Event handlers (`onclick`, `onload`, etc.)
- `@import` statements
- `expression()` CSS

## 🧪 Testing

### **Tests Implementados**

```bash
# Ejecutar tests de la funcionalidad
python -m pytest tests/routers/test_page_customization_router.py -v
```

**Casos de Prueba:**
- ✅ Health check endpoint
- ✅ Validación de datos de entrada
- ✅ Personalización con agente inexistente
- ✅ Prompts vacíos o inválidos
- ✅ Obtención de templates
- ✅ Preview de cambios
- ✅ Rollback de templates

## 📦 Instalación y Configuración

### **Backend**

1. Los archivos ya están integrados en el sistema existente
2. Router automáticamente registrado en `main.py`
3. Dependencies manejadas por el sistema existente

### **Frontend**

1. Archivos ubicados en `Client/embed/`
2. Configuración automática en mount de archivos estáticos
3. Carga automática con la página embed

### **Configuración Requerida**

```python
# main.py - Ya implementado
app.mount("/static/embed", StaticFiles(directory="Client/embed/src"), name="embed")

@app.get("/embed/{agent_id}")
async def embed_page(agent_id: str):
    return FileResponse("Client/embed/index.html")
```

## 🚀 Flujo de Usuario Completo

1. **Usuario** accede a página web deployada: `/embed/{agent_id}`
2. **Sistema** carga página con botón "✏️ Editar Página" 
3. **Usuario** hace click en botón → aparece modal
4. **Usuario** escribe prompt: *"Cambia el color de fondo a azul claro"*
5. **Frontend** valida prompt y envía request al backend
6. **Agente Modificador** analiza prompt y genera CSS seguro
7. **Sistema** valida cambios y los aplica al template
8. **Frontend** actualiza DOM en tiempo real
9. **Usuario** ve cambios aplicados inmediatamente
10. **Sistema** persiste template actualizado

## 🎯 Beneficios

### **Para Usuarios**
- ✅ **Fácil de usar**: Sin conocimiento técnico requerido
- ✅ **Intuitivo**: Comandos en lenguaje natural
- ✅ **Inmediato**: Cambios aplicados en tiempo real
- ✅ **Seguro**: Validaciones de seguridad integradas

### **Para Desarrolladores**
- ✅ **Extensible**: Fácil agregar nuevas funcionalidades
- ✅ **Mantenible**: Código bien estructurado y documentado
- ✅ **Testeable**: Suite de tests comprehensiva
- ✅ **Seguro**: Múltiples capas de validación

## 🔮 Futuras Mejoras

### **Funcionalidades Planeadas**

1. **Persistencia en Base de Datos**: Almacenamiento real de templates
2. **Preview en Tiempo Real**: Vista previa antes de aplicar
3. **Templates Predefinidos**: Galería de estilos populares
4. **Undo/Redo**: Historial de cambios más granular
5. **Colaboración**: Múltiples usuarios editando
6. **Responsive Preview**: Preview en diferentes dispositivos

### **Mejoras de Agente**

1. **LLM Más Avanzado**: Integración con modelos especializados
2. **Context Awareness**: Mejor comprensión del diseño actual
3. **Sugerencias Proactivas**: Recomendaciones automáticas
4. **Brand Guidelines**: Adherencia a guías de marca

## 📞 Soporte

Para problemas o preguntas:

1. **Issues**: Crear issue en el repositorio
2. **Logs**: Revisar logs en `/var/log/kyra/page-customization.log`
3. **Debug**: Activar modo debug en configuración
4. **Tests**: Ejecutar suite de tests para diagnosticar

---

**Versión**: 1.0.0  
**Última Actualización**: 2025-01-06  
**Mantenedor**: Equipo Kyra AI