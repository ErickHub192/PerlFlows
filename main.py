# main.py

import logging

# 🔧 AUTOMATIC FILE LOGGING: Configurar logging a archivos ANTES que todo
from logging_config import setup_file_logging
setup_file_logging()

from app.exceptions.api_exceptions import (
    ResourceNotFoundException,
    InvalidDataException,
    WorkflowProcessingException,
)
from app.exceptions import RequiresUserInputError
from app.core.constants import HTTP_UNPROCESSABLE_ENTITY
from fastapi import FastAPI, Request, Depends
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.connectors.factory import scan_handlers
from fastapi.middleware.cors import CORSMiddleware
from app.core.scheduler import start_scheduler
from app.core.auth import get_current_user_id

# ✅ LOGGING configurado automáticamente en logging_config.py


# Routers “funcionales”
from app.routers.chat_router           import router as chat_router
from app.routers.oauth_router          import router as oauth_router, oauth_apps_router
from app.routers.credentials_router    import router as credentials_router
from app.routers.login_router          import router as login_router
from app.routers.flow_execution_router import router as flow_execution_router
from app.routers.chat_session_router   import router as chat_session_router
from app.routers.db_credentials_form_router import router as db_credentials_form_router
from app.routers.auth_service_discovery import router as auth_service_discovery_router, auth_services_router

# Routers MCP de metadatos
from app.routers.connector_router        import router as connector_router
from app.routers.parameter_router        import router as parameters_router
from app.routers.ai_agent_router         import router as ai_agents_router
from app.routers.flow_router             import router as flow_router
from app.routers.smart_forms_router      import router as smart_forms_router
from app.routers.webhook_router         import router as webhook_router
from app.routers.agent_router           import router as agent_router
from app.routers.marketplace_router     import router as marketplace_router
from app.routers.telegram_router        import router as telegram_router
from app.routers.page_customization_router import router as page_customization_router
from app.routers.admin_cag_router       import router as admin_cag_router  # AGREGADO
from app.routers.frontend_logs_router   import router as frontend_logs_router  # FRONTEND LOGGING
from app.api.routes.file_discovery import router as file_discovery_router  # ✅ FIXED: Renombrado para claridad
from app.routers.llm_providers_router import router as llm_providers_router
from app.routers.parameter_diagnostics_router import router as parameter_diagnostics_router  # ✅ AGREGADO para debugging
from app.routers.reflection_router import router as reflection_router  # 🔥 NEW: Reflection capabilities

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta cuando FastAPI inicia el servidor y tiene su loop.
    1) Carga todos los handlers registrados para MCP.
    2) Arranca el scheduler de tareas.
    3) Inicializa LLM Provider Registry desde la base de datos.
    4) Inicializa Bill Agent si está habilitado.
    """
    # STARTUP MESSAGE
    print("=" + "="*80)
    print("ERICK ES EL PUTO CEO Y TIENE UNA STARTUP EXITOSA - STAY HARD!")
    print("=" + "="*80)
    logging.info("ERICK ES EL PUTO CEO Y TIENE UNA STARTUP EXITOSA - STAY HARD!")
    
    # Startup
    scan_handlers()
    start_scheduler()
    
    # Inicializar LLM Provider Registry desde la base de datos
    try:
        from app.db.database import get_db
        from app.services.provider_registry_service import ProviderRegistryService
        from app.repositories.llm_provider_repository import LLMProviderRepository
        from app.repositories.llm_model_repository import LLMModelRepository
        
        # Crear una sesión de base de datos temporal para la inicialización
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # Crear repositorios manualmente
            provider_repo = LLMProviderRepository(db)
            model_repo = LLMModelRepository(db)
            
            # Crear servicio manualmente
            registry_service = ProviderRegistryService(provider_repo, model_repo)
            await registry_service.initialize_providers()
            
            logging.info("LLM Provider Registry initialized successfully from database")
        finally:
            await db_gen.aclose()
            
    except Exception as e:
        logging.error(f"Failed to initialize LLM Provider Registry: {e}")
    
    # 🔥 OPCIÓN 2: Inicializar Redis Cache con nodos desde Supabase
    try:
        from app.services.cag_service import get_cag_service
        
        # Usar el factory para obtener RedisNodeCacheService
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # Crear service usando factory (DI)
            from app.repositories.node_repository import NodeRepository
            from app.repositories.action_repository import ActionRepository
            from app.repositories.parameter_repository import ParameterRepository
            from app.services.cag_service import RedisNodeCacheService
            
            node_repo = NodeRepository(db)
            action_repo = ActionRepository(db)
            param_repo = ParameterRepository(db)
            
            redis_cache_service = RedisNodeCacheService(node_repo, action_repo, param_repo)
            
            # Inicializar cache Redis desde BD
            await redis_cache_service.initialize_cache_from_db()
            
            logging.info("✅ Redis Node Cache initialized successfully from Supabase")
        finally:
            await db_gen.aclose()
            
    except Exception as e:
        logging.error(f"❌ Failed to initialize Redis Node Cache: {e}")
        # No fallar el startup si Redis falla
    
    # 🎯 INICIALIZAR SISTEMA DE TOKEN TRACKING
    try:
        from app.core.token_system import initialize_token_system, TokenSystemConfig
        
        # Crear sesión de BD para token system
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # Configuración según environment
            if settings.DEBUG:
                config = TokenSystemConfig.get_development_config()
                logging.info("🎯 Initializing Token System with DEVELOPMENT config")
            else:
                config = TokenSystemConfig.get_production_config()
                logging.info("🎯 Initializing Token System with PRODUCTION config")
            
            # Inicializar sistema completo
            initialize_token_system(
                db=db,
                alert_config=config.get("alert_config"),
                batch_size=config.get("batch_size", 10)
            )
            
            logging.info("✅ Token Tracking System initialized successfully")
            logging.info("📊 Auto-tracking enabled for all LLM calls")
            
        finally:
            await db_gen.aclose()
            
    except Exception as e:
        logging.error(f"❌ Failed to initialize Token System: {e}")
        # No fallar startup si token system falla
    
    # Bill Agent removed from codebase
    
    yield
    
    # Shutdown (si necesitas limpieza)

app = FastAPI(title="Kyra API", debug=settings.DEBUG, lifespan=lifespan)
# Frontend files served by shared hosting, not VPS
# app.mount("/static", StaticFiles(directory="Client/my-preact-app/dist"), name="static")
# app.mount("/static/embed", StaticFiles(directory="Client/embed/src"), name="embed")

# @app.get("/embed/{agent_id}")
# async def embed_page(agent_id: str):
#     return FileResponse("Client/embed/index.html")

# Frontend routes handled by shared hosting
# @app.get("/")
# async def dashboard():
#     return FileResponse("Client/my-preact-app/dist/index.html")

# @app.get("/login")
# async def login_page():
#     return FileResponse("Client/my-preact-app/dist/index.html")

# @app.get("/dashboard")
# async def dashboard_page():
#     return FileResponse("Client/my-preact-app/dist/index.html")

# Health check endpoint (público)
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Endpoint para verificar autenticación
@app.get("/api/auth/verify")
async def verify_auth(user_id: int = Depends(get_current_user_id)):
    return {"authenticated": True, "user_id": user_id}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5000"],  # Frontend en ambos puertos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Rutas de negocio (/api/...) ---
app.include_router(chat_router)            # /api/chat
app.include_router(oauth_router)           # /api/oauth
app.include_router(oauth_apps_router)      # /api/oauth-apps (compatibilidad frontend)
app.include_router(credentials_router)     # /api/credentials
app.include_router(login_router)           # /api/auth/login
app.include_router(chat_session_router)    # /api/chat-sessions
app.include_router(auth_service_discovery_router)  # /api/v1/auth-service-discovery
app.include_router(auth_services_router)  # /api/auth-services (compatibility for frontend)

# --- Rutas de metadatos  ---
app.include_router(connector_router)       # /api/connectors
app.include_router(parameters_router)      # /api/parameters/{action_id}/
app.include_router(ai_agents_router)       # /api/ai_agents
app.include_router(flow_router)            # /api/flows (CONSOLIDADO con workflow_router)
app.include_router(flow_execution_router)  # /api/workflow-executions
app.include_router(smart_forms_router)     # /api/smart-forms (nuevo sistema inteligente)
app.include_router(db_credentials_form_router)
app.include_router(webhook_router)
app.include_router(agent_router)
app.include_router(marketplace_router)
app.include_router(admin_cag_router)       # /api/cag, /api/admin/cag
app.include_router(frontend_logs_router)   # /api/frontend-logs (Frontend logging)
app.include_router(telegram_router)
app.include_router(page_customization_router)
app.include_router(file_discovery_router)  # /file-discovery (✅ RENAMED: Para claridad)
app.include_router(llm_providers_router)    # /api/llm (LLM providers and models)
app.include_router(parameter_diagnostics_router)  # /api/diagnostics (✅ AGREGADO para debugging)
app.include_router(reflection_router)            # /api/reflection (🔥 NEW: Workflow reflection and improvement)
# --- Manejadores globales de errores ---
@app.exception_handler(ResourceNotFoundException)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(InvalidDataException)
async def invalid_data_handler(request: Request, exc: InvalidDataException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(WorkflowProcessingException)
async def workflow_processing_handler(request: Request, exc: WorkflowProcessingException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(RequiresUserInputError)
async def user_input_required_handler(request: Request, exc: RequiresUserInputError):
    """
    Handler global para RequiresUserInputError
    Devuelve formato estructurado para que el frontend genere formularios dinámicos
    """
    return JSONResponse(
        status_code=HTTP_UNPROCESSABLE_ENTITY,  # Parámetros faltantes
        content={
            "error_type": "requires_user_input",
            "handler_name": exc.handler_name,
            "missing_info": exc.missing_info,
            "message": f"Handler '{exc.handler_name}' requires additional user input",
            "form_available": exc.missing_info.get("form_schema") is not None
        }
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True, log_level="debug")

