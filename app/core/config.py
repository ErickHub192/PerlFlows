# app/core/config.py

import os
from dotenv import load_dotenv

load_dotenv()  # Carga .env en os.environ

class Settings:
    # ——————————————————————————————————————————————————————————————————————————————————
    # Configuración general
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
    PORT: int = int(os.getenv("PORT", 5000))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # LLM / OpenAI
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4.1")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1")
    DEFAULT_EMBED_MODEL: str = os.getenv("DEFAULT_EMBED_MODEL", "text-embedding-ada-002")
    EMBED_DIMS: int = int(os.getenv("EMBED_DIMS", 1536))
    
    LLM_TIMEOUT_: float = float(os.getenv("LLM_TIMEOUT", 30.0))

    # OAuth
    OAUTH_CALLBACK_URL: str = os.getenv(
        "OAUTH_CALLBACK_URL",
        "http://localhost:5000/api/oauth/callback"
    )
    OAUTH_REDIRECT_URL: str = os.getenv(
        "OAUTH_REDIRECT_URL",
        "https://KyraAI.com/api/oauth/callback"
    )
    OAUTH_SUCCESS_URL: str = os.getenv(
        "OAUTH_SUCCESS_URL",
        "https://KyraAI.com/success"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    
    # Slack OAuth
    SLACK_CLIENT_ID: str = os.getenv("SLACK_CLIENT_ID", "")
    SLACK_CLIENT_SECRET: str = os.getenv("SLACK_CLIENT_SECRET", "")
    
    # HubSpot OAuth
    HUBSPOT_CLIENT_ID: str = os.getenv("HUBSPOT_CLIENT_ID", "")
    HUBSPOT_CLIENT_SECRET: str = os.getenv("HUBSPOT_CLIENT_SECRET", "")
    
    # Salesforce OAuth
    SALESFORCE_CLIENT_ID: str = os.getenv("SALESFORCE_CLIENT_ID", "")
    SALESFORCE_CLIENT_SECRET: str = os.getenv("SALESFORCE_CLIENT_SECRET", "")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "")
    PUBLIC_BASE_URL: str = os.getenv("KYRA_PUBLIC_URL", "http://localhost:5000")

    # HTTPX timeouts / concurrencia
    
    HTTPX_MAX_CONNECTIONS: int = int(os.getenv("HTTPX_MAX_CONNECTIONS", 100))
    HTTPX_MAX_KEEPALIVE: int = int(os.getenv("HTTPX_MAX_KEEPALIVE", 20))
    HTTPX_CONNECT_TIMEOUT: float = float(os.getenv("HTTPX_CONNECT_TIMEOUT", 2.0))
    HTTPX_READ_TIMEOUT: float = float(os.getenv("HTTPX_READ_TIMEOUT", 5.0))
    DB_MAX_CONCURRENT_QUERIES: int = int(os.getenv("DB_MAX_CONCURRENT_QUERIES", 20))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS",10))
    LLM_CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("LLM_CIRCUIT_BREAKER_THRESHOLD", 5))

    # Redis / Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", 3600))
    PLAN_CACHE_TTL : int = int(os.getenv("PLAN_CACHE_TTL", 300))
    
    #schedule redis configuration
    SCHEDULER_REDIS_DB: int = int(os.getenv("SCHEDULER_REDIS_DB", 1))
    REDIS_HOST : str = os.getenv("REDIS_HOST","localhost")
    REDIS_PORT : int = int(os.getenv("REDIS_PORT",6379))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # Security System Configuration
    SECURITY_SYSTEM_ENABLED: bool = os.getenv("SECURITY_SYSTEM_ENABLED", "true").lower() in ("1", "true", "yes")
    SECURITY_RATE_LIMIT_ENABLED: bool = os.getenv("SECURITY_RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")
    SECURITY_SANDBOX_ENABLED: bool = os.getenv("SECURITY_SANDBOX_ENABLED", "true").lower() in ("1", "true", "yes")
    SECURITY_MONITOR_ENABLED: bool = os.getenv("SECURITY_MONITOR_ENABLED", "true").lower() in ("1", "true", "yes")
    SECURITY_KILL_SWITCH_ENABLED: bool = os.getenv("SECURITY_KILL_SWITCH_ENABLED", "true").lower() in ("1", "true", "yes")
    
    # Rate Limiting Configuration
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("DEFAULT_RATE_LIMIT_PER_MINUTE", 10))
    DEFAULT_RATE_LIMIT_PER_HOUR: int = int(os.getenv("DEFAULT_RATE_LIMIT_PER_HOUR", 100))
    DEFAULT_COST_LIMIT_PER_DAY: float = float(os.getenv("DEFAULT_COST_LIMIT_PER_DAY", 50.0))
    DEFAULT_CONCURRENT_LIMIT: int = int(os.getenv("DEFAULT_CONCURRENT_LIMIT", 3))
    
    # Security Sandbox Configuration
    SANDBOX_MAX_EXECUTION_TIME: int = int(os.getenv("SANDBOX_MAX_EXECUTION_TIME", 30))
    SANDBOX_MAX_MEMORY_MB: int = int(os.getenv("SANDBOX_MAX_MEMORY_MB", 512))
    SANDBOX_MAX_CPU_PERCENT: float = float(os.getenv("SANDBOX_MAX_CPU_PERCENT", 80.0))
    SANDBOX_MAX_NETWORK_REQUESTS: int = int(os.getenv("SANDBOX_MAX_NETWORK_REQUESTS", 10))
    
    # Handler Validation Configuration
    HANDLER_VALIDATION_LEVEL: str = os.getenv("HANDLER_VALIDATION_LEVEL", "standard")  # basic, standard, strict, paranoid
    HANDLER_VALIDATION_CACHE_TTL: int = int(os.getenv("HANDLER_VALIDATION_CACHE_TTL", 86400))  # 24 hours
    
    # Security Monitoring Configuration
    SECURITY_ALERT_WEBHOOK_URL: str = os.getenv("SECURITY_ALERT_WEBHOOK_URL", "")
    SECURITY_MONITOR_RETENTION_DAYS: int = int(os.getenv("SECURITY_MONITOR_RETENTION_DAYS", 7))
    SECURITY_METRICS_COLLECTION_INTERVAL: int = int(os.getenv("SECURITY_METRICS_COLLECTION_INTERVAL", 10))  # seconds
    # ——————————————————————————————————————————————————————————————————————————————————
    # Variables de CAG (Cache-Augmented Generation)
    # Si es True, se omite la búsqueda semántica y se utiliza el catálogo
    # completo de nodos almacenado en caché para una respuesta más rápida.
    CAG_ENABLED: bool = os.getenv("CAG_ENABLED", "false").lower() in ("1", "true", "yes")
    CAG_CONTEXT_CACHE_KEY: str = os.getenv("CAG_CONTEXT_CACHE_KEY", "cag:context")
    CAG_CACHE_DIR: str = os.getenv("CAG_CACHE_DIR", "cache")
    CAG_BATCH_SIZE: int = int(os.getenv("CAG_BATCH_SIZE", 20))
    CAG_TIMEOUT_SECONDS: int = int(os.getenv("CAG_TIMEOUT_SECONDS", 60))
    CAG_STARTUP_TIMEOUT: int = int(os.getenv("CAG_STARTUP_TIMEOUT", 30))
    CAG_MAX_ATTEMPTS: int = int(os.getenv("CAG_MAX_ATTEMPTS", 1))

    # Guardrails / Telemetry
    GUARDRAILS_TIMEOUT: int = int(os.getenv("GUARDRAILS_TIMEOUT", 30))
    OTEL_ENDPOINT: str = os.getenv(
        "OTEL_ENDPOINT",
        "http://otel-collector:4318/v1/traces",
    )
    
    #DROPBOX AUTH--------------------------------------------------------
    DROPBOX_CLIENT_ID: str = os.getenv("DROPBOX_CLIENT_ID", "")
    DROPBOX_CLIENT_SECRET: str = os.getenv("DROPBOX_CLIENT_SECRET", "")
    DROPBOX_REDIRECT_URI: str = os.getenv(
        "DROPBOX_REDIRECT_URI",
        "https://tu.dominio.com/api/oauth/callback?service=dropbox",
    )
    
    # ——————————————————————————————————————————————————————————————————————————————————
    # Universal Discovery & Enhanced Workflow Configuration
    # ——————————————————————————————————————————————————————————————————————————————————
    
    # Feature Flags
    USE_UNIVERSAL_DISCOVERY: bool = os.getenv("USE_UNIVERSAL_DISCOVERY", "true").lower() in ("1", "true", "yes")
    USE_ENHANCED_SELECTION: bool = os.getenv("USE_ENHANCED_SELECTION", "true").lower() in ("1", "true", "yes")
    USE_WORKFLOW_ENGINE: bool = os.getenv("USE_WORKFLOW_ENGINE", "false").lower() in ("1", "true", "yes")
    
    # Discovery Configuration
    DISCOVERY_MAX_FILES_PER_PROVIDER: int = int(os.getenv("DISCOVERY_MAX_FILES_PER_PROVIDER", "10"))
    
    # Workflow Engine Configuration
    WORKFLOW_PARALLEL_DISCOVERY: bool = os.getenv("WORKFLOW_PARALLEL_DISCOVERY", "true").lower() in ("1", "true", "yes")
    WORKFLOW_MAX_OAUTH_REQUIREMENTS: int = int(os.getenv("WORKFLOW_MAX_OAUTH_REQUIREMENTS", "3"))
    
    # OAuth Flow Configuration  
    OAUTH_MAX_PROVIDERS_PER_REQUEST: int = int(os.getenv("OAUTH_MAX_PROVIDERS_PER_REQUEST", "3"))
    OAUTH_CONTEXTUAL_MESSAGES: bool = os.getenv("OAUTH_CONTEXTUAL_MESSAGES", "true").lower() in ("1", "true", "yes")
    
    # Enhanced Workflow Configuration
    ENHANCED_WORKFLOW_TIMEOUT: int = int(os.getenv("ENHANCED_WORKFLOW_TIMEOUT", "30"))
    ENHANCED_AUTO_EXECUTE: bool = os.getenv("ENHANCED_AUTO_EXECUTE", "false").lower() in ("1", "true", "yes")
    
    # Fallback Configuration
    ALWAYS_FALLBACK_TO_TRADITIONAL: bool = os.getenv("ALWAYS_FALLBACK_TO_TRADITIONAL", "true").lower() in ("1", "true", "yes")
    
    # ——————————————————————————————————————————————————————————————————————————————————
    # Bill Meta Agent Configuration - REMOVED
    # ——————————————————————————————————————————————————————————————————————————————————
    
    # Admin User IDs (for configuration access)
    ADMIN_USER_IDS: list = [int(x.strip()) for x in os.getenv("ADMIN_USER_IDS", "1").split(",") if x.strip().isdigit()]


# Instancia única que usarás en toda la app
settings = Settings()
