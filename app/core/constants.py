"""
Application Constants
Common constants used throughout the application
"""

# HTTP Response Status Codes
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_SUCCESS = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204

# Pagination Defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# Discovery Limits
MAX_DISCOVERY_RESULTS = 100
DEFAULT_DISCOVERY_LIMIT = 50

# LLM Defaults
DEFAULT_MAX_TOKENS = 1536
DEFAULT_TEMPERATURE = 0.7

# Cache TTL (seconds)
DISCOVERY_CACHE_TTL = 900  # 15 minutes
SERVICE_INFO_CACHE_TTL = 300  # 5 minutes

# File Size Limits (bytes)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TEXT_LENGTH = 100000  # 100K characters

# Retry Configuration
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds

# Google API Discovery
GOOGLE_DISCOVERY_VERSION = "v1"

# Database Connection Pool
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20

# Session and Token Expiry
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Rate Limiting
DEFAULT_RATE_LIMIT = 100  # requests per minute
BURST_RATE_LIMIT = 200

# Webhook Configuration
WEBHOOK_TIMEOUT_SECONDS = 30
MAX_WEBHOOK_RETRIES = 3

# Chat Service Keys
CLARIFY_ANSWERS_KEY = "clarify_answers"
NODE_IDS_KEY = "node_ids"
WORKFLOW_SPEC_KEY = "workflow_spec"
EXECUTION_CONTEXT_KEY = "execution_context"