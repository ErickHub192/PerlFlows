# Chat System Architecture

## 🎯 **SISTEMA ACTUAL (Estilo ChatGPT)**

### **Flujo de Nuevo Chat:**
1. Usuario hace clic en "Nuevo Chat" → Redirige a `/chat` (sin ID)
2. En `/chat` → Muestra `NewChatView` (interfaz limpia, sin backend)
3. Usuario escribe primer mensaje → Crea sesión real en backend → Redirige a `/chat/[uuid]`
4. `ChatView` maneja mensajes con UUID real

### **Componentes:**
- **NewChatView** (`/pages/NewChatView.jsx`) → Página limpia en `/chat`
- **ChatView** (`/pages/ChatView.jsx`) → Maneja chats reales con UUID
- **SidebarFixed** → "Nuevo Chat" va a `/chat`

### **Store (chatStore.js):**
- `addChat()` → Crea sesión real en backend
- `sendMessage()` → Solo para UUIDs reales
- `fetchMessages()` → Solo para UUIDs reales
- ❌ **NO tiene** `startNewChat()` (eliminado)

## 🚨 **CÓDIGO LEGACY ELIMINADO**

### **❌ NO usar estos patrones:**
```javascript
// ❌ ELIMINADO: Chats temporales
const tempId = 'temp-' + Date.now();
if (chatId.startsWith('temp-')) { ... }

// ❌ ELIMINADO: startNewChat function
startNewChat: () => { ... }

// ❌ ELIMINADO: Conversión temp → real
if (isTemporaryChat) { ... }
```

### **✅ PATRÓN CORRECTO:**
```javascript
// ✅ Nuevo Chat
route('/chat', true); // → NewChatView

// ✅ Chat Real
route(`/chat/${uuid}`, true); // → ChatView
```

## 📋 **BASE DE DATOS**

### **Solo se guardan:**
- Chats con al menos 1 mensaje
- UUIDs reales generados por backend
- NO se guardan chats vacíos o temporales

### **Endpoints:**
- `POST /api/chats/` → Crear sesión real
- `GET /api/chats/{uuid}/messages` → Obtener mensajes
- `POST /api/chat` → Enviar mensaje

## 🔒 **REGLAS CRÍTICAS**

### **1. NO reintroducir lógica temporal:**
- No crear IDs que empiecen con `temp-`
- No manejar estados intermedios
- No conversiones de temporal → real

### **2. Mantener flujo simple:**
- `/chat` = NewChatView (limpio)
- `/chat/[uuid]` = ChatView (real)

### **3. Solo UUIDs reales en store:**
- `chatHistories` solo contiene UUIDs del backend
- `chats` array solo sesiones reales
- No estados temporales en memoria

## 🚀 **Si necesitas modificar:**

### **Para agregar funciones:**
1. Mantener flujo: NewChatView → create real session → ChatView
2. NO introducir estados temporales
3. Seguir patrón ChatGPT

### **Para debugging:**
- Verificar que `/chat` muestre NewChatView
- Verificar que `/chat/[uuid]` muestre ChatView
- NO debe haber chats `temp-*` en store

## ⚠️ **ANTI-PATRONES**

### **❌ NO hacer esto:**
```javascript
// ❌ NO: Crear IDs temporales
const tempId = 'temp-' + Date.now();

// ❌ NO: Lógica condicional por tipo de chat
if (chatId.startsWith('temp-')) {
  // conversion logic
} else {
  // real chat logic
}

// ❌ NO: Múltiples flujos de creación
startNewChat() // temporal
createRealChat() // real
```

### **✅ SÍ hacer esto:**
```javascript
// ✅ SÍ: Un solo flujo
route('/chat'); // → NewChatView
// User types → create real session → route to real chat

// ✅ SÍ: Solo UUIDs reales en lógica
sendMessage(realUuid, content);
```

---

**Fecha de implementación:** 2025-06-28  
**Versión:** ChatGPT-style v1.0  
**Mantenedor:** Sistema refactorizado para eliminar complejidad temporal