# Kyra: Plataforma de Automatización Inteligente

## Descripción General
Kyra es una plataforma modular que permite a los usuarios describir en lenguaje natural acciones o automatizaciones, y el sistema las ejecuta integrando servicios como Google Drive, Gmail, APIs externas y más. Utiliza IA para interpretar instrucciones y orquestar flujos de trabajo (workflows) personalizados con arquitectura basada en **WorkflowEngine**.

## Características Principales
- **Automatización por lenguaje natural:** El usuario describe lo que quiere hacer y Kyra lo ejecuta.
- **Workflows dinámicos y secuenciales:** Crear, ejecutar y monitorear flujos con dependencias y ramificaciones.
- **Integración con servicios externos:** Soporte para Google, Microsoft, Telegram, Gmail, Google Sheets, etc.
- **Discovery inteligente:** CAG (Cache-Augmented Generation) para selección automática de servicios.
- **Reflection loops:** Auto-optimización de workflows basada en resultados de ejecución.
- **Simulación completa (Dry-Run):** Ejecutar workflows sin afectar sistemas externos.
- **Autenticación OAuth:** Integración segura con servicios de terceros.
- **Frontend moderno:** Interfaz web construida con Preact.

## Nueva Arquitectura (2025)

### WorkflowEngine - Motor Principal
```
WorkflowEngine
├── Discovery Providers
│   ├── CAGDiscoveryProvider (selección inteligente de nodos)
│   └── UniversalDiscoveryProvider (discovery de archivos)
├── Planning Strategies  
│   └── ClassicPlanningStrategy (planificación secuencial)
└── Execution
    ├── WorkflowRunnerService (ejecución real/simulada)
    └── ReflectHandler (loops de reflexión)
```

**Flujo principal:**
1. **LLM selecciona nodos** desde contexto CAG completo
2. **Discovery secuencial** procesando paso a paso con dependencias
3. **Planning estratégico** generando plan de ejecución ordenado
4. **Ejecución con reflection** optimizando automáticamente

### Características Avanzadas

#### 🎯 Targeted Discovery
- Usuario selecciona servicios específicos (Gmail, Google Sheets, etc.)
- Discovery solo busca en servicios seleccionados
- Reduce latencia y mejora precisión

#### 🔄 Reflection Loops
- Plan → Act → Reflect → Iterate
- Auto-mejora de workflows basada en resultados
- Máximo 3 iteraciones con satisfaction scoring

#### ⚡ Ejecución Secuencial
- Procesa workflows paso a paso respetando dependencias
- Soporte para ramificaciones condicionales
- Manejo de errores y reintentos

## Estructura del Proyecto

```
├── main.py / main_console.py         # Puntos de entrada
├── app/
│   ├── workflow_engine/             # 🆕 Motor de workflows principal
│   │   ├── core/                    # WorkflowEngine, interfaces
│   │   ├── discovery/               # Providers de discovery (CAG, Universal)
│   │   └── planning/                # Estrategias de planificación
│   ├── services/
│   │   ├── chat_service_clean.py    # 🔄 Chat coordinador (sin duplicación)
│   │   ├── workflow_runner_service.py # Ejecución real/simulada
│   │   ├── cag_service.py          # Cache-Augmented Generation
│   │   └── [otros servicios]
│   ├── ai/                          # Lógica de IA y herramientas LLM
│   ├── authenticators/              # Autenticadores OAuth y personalizados
│   ├── handlers/                    # Handlers de acciones y nodos
│   ├── routers/                     # Endpoints de la API
│   ├── db/                          # Modelos y acceso a base de datos
│   └── [estructura estándar API]
├── Client/my-preact-app/            # Frontend Preact
└── alembic/                         # Migraciones de base de datos
```

## ¿Cómo funciona?

### Flujo Nuevo (WorkflowEngine)
1. **Usuario describe acción** → "Envía archivos PDF de Drive a mi correo"
2. **CAG selecciona nodos** → LLM elige servicios relevantes del catálogo completo
3. **Discovery secuencial** → Procesa paso a paso: Drive → Email con dependencias
4. **Planning estratégico** → Genera plan ordenado con metadata de parámetros
5. **Ejecución con reflection** → Ejecuta, evalúa, mejora automáticamente
6. **Monitoreo** → Usuario ve progreso en tiempo real desde frontend

### Flujo con Servicios Seleccionados
1. **Usuario selecciona servicios** → Gmail + Google Sheets
2. **Targeted discovery** → Solo busca en servicios seleccionados
3. **Ejecución optimizada** → Mayor velocidad y precisión

## Simulación de Flujos (Dry-Run)

### ✨ Funcionalidad Completa Implementada

**Frontend:**
- Botón "Simular" en `WorkflowCard` y `WorkflowSidePanel`
- Modal `SimulateDialog` con visualización de resultados
- Hook `useDryRun()` para gestión de estado

**Backend:**
- Endpoint `/api/flows/dry-run` completamente funcional
- `WorkflowRunnerService` con parámetro `simulate=True`
- Generación automática de datos stub con metadata

**Características:**
- ✅ **Ejecución sin efectos:** No envía emails, no modifica archivos
- ✅ **Datos realistas:** Outputs stub con formato real
- ✅ **Validación completa:** Verifica parámetros y lógica
- ✅ **Visualización UI:** Resultados paso a paso en interfaz
- ✅ **Testing integrado:** Framework de testing automático

### Ejemplo de Uso
```bash
curl -X POST "http://localhost:5000/api/flows/dry-run" \
  -H "Content-Type: application/json" \
  -d '{
        "flow_id": "<uuid>",
        "steps": [
          {
            "node_name": "Gmail", 
            "action": "send_messages", 
            "params": {"to": "test@gmail.com"}
          }
        ],
        "user_id": 1,
        "test_inputs": {"attachments": ["file1.pdf"]}
      }'
```

**Respuesta:**
```json
{
  "status": "success",
  "steps": [
    {
      "status": "success",
      "output": {
        "stub": true,
        "message_id": "sim-msg-123",
        "sent_to": "test@gmail.com"
      }
    }
  ]
}
```

## Pasos Condicionales (Branch)

Workflows pueden incluir nodos `branch` para decisiones durante ejecución:

```json
{
  "start_id": "11111111-1111-1111-1111-111111111111",
  "steps": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "type": "branch",
      "condition": "{{file_count}} > 5",
      "next_on_true": "send_email",
      "next_on_false": "send_slack"
    }
  ]
}
```

## Autenticación OAuth

Sistema completo de OAuth 2.0 con múltiples proveedores:

### Flujo OAuth
1. **Inicio:** `GET /api/oauth/initiate?service=google`
2. **Redirección:** Usuario autoriza en proveedor
3. **Callback:** `GET /api/oauth/callback?service=google&code=...`
4. **Almacenamiento:** Tokens cifrados por usuario

### Proveedores Soportados
- Google (Gmail, Drive, Sheets, Calendar)
- Microsoft (Outlook, OneDrive)
- Dropbox
- Slack
- Salesforce
- HubSpot

## Instalación y Ejecución

### Requisitos
- Python 3.11+
- PostgreSQL con extensión pgvector
- Redis
- Node.js 18+ (para frontend)

### Setup Completo
1. **Clonar y configurar:**
   ```bash
   git clone <repo>
   cd kyra
   cp .env.example .env
   # Configurar DATABASE_URL y otras variables
   ```

2. **Base de datos:**
   ```bash
   # PostgreSQL con pgvector
   DATABASE_URL=postgresql+psycopg2://kyra:kyra@localhost:5432/kyradb
   ```

3. **Backend Python:**
   ```bash
   pip install -r requirements.txt
   python seed_nodes.py
   python embed_nodes.py
   ```

4. **Ejecutar backend:**
   ```bash
   python main.py
   # o para desarrollo:
   uvicorn main:app --reload --port 5000
   ```

5. **Frontend:**
   ```bash
   cd Client/my-preact-app
   npm install
   npm run dev
   ```

6. **Testing:**
   ```bash
   # Tests unitarios
   pytest tests/
   # Tests E2E
   npm run test:e2e
   ```

### Variables de Entorno Clave
```env
# Base de datos
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/kyradb

# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# Funcionalidades
CAG_ENABLED=true              # Cache-Augmented Generation
REFLECTION_ENABLED=true       # Reflection loops
MAX_WORKFLOW_STEPS=10         # Límite de pasos por workflow

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
# [otros proveedores OAuth]
```

## Modo AI y Deploy de Agentes

### Modo AI
- Toggle en frontend para habilitar/deshabilitar IA
- Generación automática vs manual de workflows
- Estado persistente en localStorage

### Deploy de Agentes
- Modal de despliegue para agentes IA
- Soporte para Telegram, Web Widget
- Configuración de canales y credenciales

```bash
# Deploy a Telegram
curl -X POST http://localhost:5000/api/agents/AGENT_ID/deploy \
  -H 'Content-Type: application/json' \
  -d '{"channel":"telegram","bot_token":"TOKEN"}'
```

## Extensión y Personalización

### Agregar Nuevos Handlers
```python
# app/handlers/mi_nuevo_handler.py
@tool_handler("mi_servicio", "mi_accion")
class MiNuevoHandler:
    async def handle(self, params: dict, context: dict):
        # Lógica del handler
        return {"status": "success", "data": "..."}
```

### Agregar Discovery Provider
```python
# app/workflow_engine/discovery/mi_provider.py
class MiDiscoveryProvider(IDiscoveryProvider):
    async def discover_capabilities(self, user_message, user_id, context):
        # Lógica de discovery
        return [CapabilityInfo(...)]
```

### Agregar Planning Strategy
```python
# app/workflow_engine/planning/mi_strategy.py
class MiPlanningStrategy(IPlanningStrategy):
    async def plan_workflow(self, intent, capabilities, context):
        # Lógica de planificación
        return [WorkflowStep(...)]
```

## API Endpoints Principales

### Chat y Workflows
- `POST /api/chat/process` - Procesar mensaje de chat
- `POST /api/chat/process-with-services` - Chat con servicios seleccionados
- `POST /api/workflows/create` - Crear workflow
- `GET /api/workflows/{id}/status` - Estado de workflow

### Simulación
- `POST /api/flows/dry-run` - Simular workflow
- `GET /api/flows/{id}/spec` - Especificación de workflow

### OAuth y Credenciales
- `GET /api/oauth/initiate` - Iniciar OAuth
- `GET /api/oauth/callback` - Callback OAuth
- `GET /api/credentials` - Listar credenciales
- `POST /api/credentials` - Crear/actualizar credenciales

### Agentes
- `POST /api/agents` - Crear agente
- `POST /api/agents/{id}/deploy` - Desplegar agente
- `GET /api/agents/{id}/runs` - Historial de ejecuciones

## Arquitectura Técnica

### Eliminación de Duplicaciones (2025)
- ❌ **OrchestratorService eliminado** - funcionalidad movida a WorkflowEngine
- ✅ **ChatService simplificado** - solo coordinación de mensajes
- ✅ **WorkflowEngine centralizado** - planning + discovery + execution
- ✅ **Un solo sistema de simulación** - WorkflowRunnerService

### Patrones de Diseño
- **Factory Pattern:** Creación de providers y strategies
- **Strategy Pattern:** Algoritmos de planning intercambiables
- **Observer Pattern:** Reflection loops y monitoring
- **Dependency Injection:** Servicios y repositorios

### Performance
- **CAG Context:** Una sola llamada por workflow (eliminada duplicación)
- **Discovery Secuencial:** Procesamiento paso a paso optimizado
- **Async/Await:** Operaciones no bloqueantes
- **Redis Cache:** Cacheo de contextos y resultados

## Testing

### Tipos de Tests
- **Unitarios:** Services, handlers, utilities
- **Integración:** WorkflowEngine, discovery, planning
- **E2E:** Frontend + backend completo
- **Simulación:** Dry-run testing automático

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/workflow_engine/ -v
pytest tests/services/test_chat_service.py -v

# Tests E2E
npm run test:e2e
```

## Monitoreo y Logs

### Logging Estructurado
- Niveles: DEBUG, INFO, WARNING, ERROR
- Contexto: user_id, workflow_id, step_id
- Métricas: duración, éxito/fallo, reflection iterations

### Métricas Clave
- Workflows ejecutados/simulados
- Reflection iterations promedio
- OAuth connections activas
- Error rates por servicio

## Seguridad

### Medidas Implementadas
- **Tokens cifrados:** Credenciales almacenadas como BYTEA
- **OAuth seguro:** State validation, PKCE
- **Rate limiting:** Prevención de abuso
- **Input validation:** Sanitización de parámetros
- **Sandboxing:** Ejecución aislada de handlers

## Roadmap y Mejoras Futuras

### Q1 2025
- [ ] Workflows de voz (speech-to-text)
- [ ] Marketplace de templates expandido
- [ ] Analytics dashboard
- [ ] Multi-tenant support

### Q2 2025
- [ ] Mobile app (React Native)
- [ ] Collaborative workflows
- [ ] Advanced branching logic
- [ ] Custom LLM integration

## Licencia
Este proyecto se distribuye bajo una licencia propietaria. Consulta el archivo [LICENSE](../LICENSE) para más detalles.

---

> Proyecto desarrollado por Erick Solin. Nueva arquitectura 2025 con WorkflowEngine, eliminación de duplicaciones y sistema completo de simulación. Para dudas o contribuciones, abre un issue o pull request.