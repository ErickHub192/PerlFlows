# app/db/models.py

import uuid
from datetime import datetime, timezone
from enum import Enum
import secrets

from sqlalchemy import (
    Column,
    Enum as PgEnum,
    Integer,
    String,
    Text,
    TIMESTAMP,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
    BigInteger,
    Float,
    text,
    Boolean,
    JSON,
    LargeBinary,
    Computed,
)
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from decimal import Decimal
from sqlalchemy import Date, DECIMAL

from app.db.database import Base


# —————————————————————————————————————————————————————
#  Enums
# —————————————————————————————————————————————————————


class NodeType(str, Enum):
    trigger = "trigger"
    action = "action"
    transform = "transform"
    ai = "ai"
    subflow = "subflow"


class ActionType(str, Enum):
    Trigger = "Trigger"
    Action = "Action"


class TemplateCategory(str, Enum):
    BUSINESS_SALES = "business_sales"
    FINANCE_ACCOUNTING = "finance_accounting" 
    CUSTOMER_SERVICE = "customer_service"
    MARKETING_CONTENT = "marketing_content"
    ECOMMERCE_RETAIL = "ecommerce_retail"
    MEXICO_LATAM = "mexico_latam"
    DEVELOPMENT_DEVOPS = "development_devops"


class ParamType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"
    file = "file"


class UsageMode(str, Enum):
    """How this connector can be used inside a workflow."""

    step = "step"  # normal workflow step
    tool = "tool"  # used only as an agent tool
    step_and_tool = "step_and_tool"
    function = "function"  # exposed as a function for the LLM


class AgentStatus(str, Enum):
    queued = "queued"
    running = "running"
    paused = "paused"
    succeeded = "succeeded"
    failed = "failed"


class MemoryKind(str, Enum):
    vector = "vector"
    episodic = "episodic"


# —————————————————————————————————————————————————————
#  Modelos principales
# —————————————————————————————————————————————————————


class Node(Base):
    __tablename__ = "nodes"

    node_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    slug = Column(
        String, index=True, nullable=False
    )  # 2.1 versión (e.g. "google_sheets_v2")
    node_type = Column(PgEnum(NodeType), nullable=False)
    default_auth = Column(String, nullable=True)
    embedding = Column(
        Vector(1536), nullable=True
    )  # 2.9 dims=1536 para text-embedding-3-small
    use_case = Column(Text, nullable=True)
    usage_mode = Column(
        PgEnum(UsageMode), nullable=False, server_default=UsageMode.step.value
    )

    actions = relationship(
        "Action",
        back_populates="node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Action(Base):
    __tablename__ = "actions"

    action_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    action_type = Column(  # 2.2 renombrado desde is_trigger
        PgEnum(ActionType, name="action_type"),
        nullable=False,
        server_default=ActionType.Action.value,
    )
    # Auto-trigger auth columns
    auth_policy_id = Column(
        Integer,
        ForeignKey("auth_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_required = Column(Boolean, nullable=False, server_default=text("false"))
    custom_scopes = Column(ARRAY(String), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    node = relationship("Node", back_populates="actions")
    parameters = relationship(
        "Parameter", back_populates="action", cascade="all, delete-orphan"
    )
    auth_policy = relationship("AuthPolicy", foreign_keys=[auth_policy_id])

    @property
    def is_trigger(self) -> bool:
        """
        Indica si esta acción pertenece al tipo 'trigger'.
        Retorna True si action_type == ActionType.trigger.
        """
        return self.action_type == ActionType.Trigger


class Parameter(Base):
    __tablename__ = "parameters"

    param_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("actions.action_id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required = Column(Boolean, nullable=False, server_default=text("true"))
    param_type = Column(  # 2.3 tipo enum limitado
        PgEnum(ParamType, name="param_type"),
        nullable=False,
        server_default=ParamType.string.value,
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    action = relationship("Action", back_populates="parameters")


class AIAgent(Base):
    __tablename__ = "ai_agents"

    agent_id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(String, nullable=False, unique=True)
    default_prompt = Column(Text, nullable=True)
    tools = Column(ARRAY(String), nullable=True)
    memory_schema = Column(JSONB, nullable=True)
    status = Column(
        PgEnum(AgentStatus, name="agentstatus"),
        nullable=False,
        server_default=AgentStatus.queued.value,
    )
    planner_state = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    
    # Activation Configuration - Triggers como nodos seleccionables
    activation_type = Column(String, nullable=False, default="manual")  # "manual", "triggered"
    trigger_config = Column(JSONB, nullable=True)  # Configuración del trigger seleccionado
    is_active = Column(Boolean, nullable=False, default=True)  # Si está activo para triggers automáticos
    last_triggered = Column(DateTime(timezone=True), nullable=True)  # Última ejecución por trigger
    
    # LLM Configuration - Enhanced to reference LLM providers and models
    llm_provider_id = Column(
        PgUUID(as_uuid=True), 
        ForeignKey("llm_providers.provider_id", ondelete="RESTRICT"), 
        nullable=True,
        index=True
    )
    llm_model_id = Column(
        PgUUID(as_uuid=True), 
        ForeignKey("llm_models.model_id", ondelete="RESTRICT"), 
        nullable=True,
        index=True
    )
    model = Column(String, nullable=True)  # Fallback for backward compatibility
    temperature = Column(Float, nullable=False, default=0.7)
    max_iterations = Column(Integer, nullable=False, default=3)
    
    # Usage tracking for cost analytics
    total_input_tokens = Column(BigInteger, nullable=False, default=0)
    total_output_tokens = Column(BigInteger, nullable=False, default=0)
    total_cost = Column(DECIMAL(precision=12, scale=6), nullable=False, default=0)
    webhook_secret = Column(
        String, nullable=False, default=lambda: secrets.token_urlsafe(24)
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<AIAgent(name={self.name!r}, model={self.model!r}, "
            f"temp={self.temperature}, max_iter={self.max_iterations})>"
        )

    # Relationships
    llm_provider = relationship("LLMProvider", foreign_keys=[llm_provider_id], lazy="selectin")
    llm_model = relationship("LLMModel", foreign_keys=[llm_model_id], lazy="selectin") 
    memories = relationship(
        "AgentMemory",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # Helper properties for backward compatibility and easy access
    @property
    def effective_model(self) -> str:
        """Returns the effective model string - prioritizes LLM model reference over fallback"""
        if self.llm_model and self.llm_model.model_key:
            return self.llm_model.model_key
        return self.model or "gpt-4o-mini"
    
    @property
    def provider_name(self) -> str:
        """Returns the provider name if available"""
        if self.llm_provider:
            return self.llm_provider.name
        return "Unknown"
    
    @property
    def model_display_name(self) -> str:
        """Returns the model display name if available"""
        if self.llm_model:
            return self.llm_model.display_name
        return self.effective_model


class FlowExecution(Base):
    __tablename__ = "flow_executions"
    __table_args__ = (
        Index(
            "ix_flow_executions_flow_id", "flow_id"
        ),  # 2.5 index para búsquedas rápidas
        Index("ix_flow_executions_status", "status"),
    )

    execution_id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    flow_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("flows.flow_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flow_spec = Column(JSONB, nullable=False)
    inputs = Column(JSONB, nullable=False)
    outputs = Column(JSONB, nullable=True)
    cost = Column(Float, nullable=True)

    status = Column(
        String,  # 2.5 default creado, cambia a "running" en tu lógica
        nullable=False,
        server_default=text("'created'"),
    )
    error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)

    flow = relationship("Flow", back_populates="executions")
    steps = relationship(  # 2.2 relación de pasos detallados
        "FlowExecutionStep",
        back_populates="execution",
        cascade="all, delete-orphan",
    )


class Flow(Base):
    __tablename__ = "flows"

    flow_id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(String, nullable=False)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    spec = Column(JSONB, nullable=False)
    spec_version = Column(
        Integer,  # 2.4 versión de spec para migraciones/rollback
        nullable=False,
        server_default=text("1"),
    )
    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    executions = relationship(
        "FlowExecution",
        back_populates="flow",
        cascade="all, delete-orphan",
    )

    triggers = relationship(
        "Trigger",
        back_populates="flow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Relationship to chat session
    chat_session = relationship(
        "ChatSession",
        foreign_keys=[chat_id],
        lazy="selectin",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    credentials = relationship(
        "Credential", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_states = relationship(
        "OAuthState", back_populates="user", cascade="all, delete-orphan"
    )


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chat_id = Column(
        PgUUID(as_uuid=True),
        nullable=True,  # 🌍 GLOBAL: Allow NULL for global credentials
        index=True,
    )
    service_id = Column(String(100), nullable=False, index=True)
    
    # OAuth configuration columns for future user-provided credentials
    provider = Column(String(50), nullable=True)  # google, microsoft, slack, etc.
    client_id = Column(String(255), nullable=True)  # For user-provided OAuth credentials
    client_secret = Column(LargeBinary, nullable=True)  # Encrypted like tokens
    
    config = Column(JSONB, nullable=True)

    # 2.7 cifrar tokens como LargeBinary
    access_token = Column(LargeBinary, nullable=True)
    refresh_token = Column(LargeBinary, nullable=True)

    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    scopes = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="credentials")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "service_id",
            "chat_id",
            name="uq_user_service_chat",
        ),
    )


class OAuthState(Base):
    __tablename__ = "oauth_states"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "service_id", name="uq_oauth_states_user_provider_service"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider = Column(String, nullable=False)
    service_id = Column(String, nullable=False)  # ✅ NUEVO: service_id agnóstico
    chat_id = Column(PgUUID(as_uuid=True), nullable=False)  # ✅ NUEVO: chat_id para credentials
    state = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    user = relationship("User", back_populates="oauth_states")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    agent_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("ai_agents.agent_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = Column(
        PgEnum(MemoryKind, name="memorykind"),
        nullable=False,
        server_default=MemoryKind.episodic.value,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    embedding = Column(Vector(1536), nullable=False)  # 2.9 dims=1536

    # 2.8 renombrado a singular y default {}
    metadatas = Column(JSONB, nullable=False, server_default=text("'{}'"))
    content = Column(Text, nullable=False)

    agent = relationship(
        "AIAgent",
        back_populates="memories",
        lazy="joined",
    )


class Trigger(Base):
    __tablename__ = "triggers"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_trigger_job_id"),  # 2.6 evitar duplicados
    )

    trigger_id = Column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    flow_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("flows.flow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("actions.action_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_type = Column(String, nullable=False)
    trigger_args = Column(JSONB, nullable=True)
    job_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, server_default="active")

    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    flow = relationship("Flow", back_populates="triggers")
    node = relationship("Node")
    action = relationship("Action")


# —————————————————————————————————————————————————————
#  Detalle de ejecución de Flows
# —————————————————————————————————————————————————————


class FlowExecutionStep(Base):
    __tablename__ = "flow_execution_steps"

    step_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("flow_executions.execution_id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id = Column(PgUUID(as_uuid=True), nullable=False)
    action_id = Column(PgUUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False)  # “running” | “ok” | “error”
    error = Column(Text, nullable=True)
    started_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)

    execution = relationship("FlowExecution", back_populates="steps")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("flows.flow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    headers = Column(JSONB, nullable=True)
    payload = Column(JSONB, nullable=True)
    received_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title = Column(String, nullable=False, default="Nuevo chat")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # 🔧 COMPOSITE INDEX: Optimizar queries de sidebar (user_id + created_at DESC)
    __table_args__ = (
        Index('idx_chat_sessions_user_created', 'user_id', 'created_at'),
    )

    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    message_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role = Column(String, nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session = relationship("ChatSession", back_populates="messages")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("ai_agents.agent_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    status = Column(
        PgEnum(AgentStatus, name="agentstatus"),
        nullable=False,
        server_default=AgentStatus.queued.value,
    )
    goal = Column(Text, nullable=True)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    agent = relationship("AIAgent")


class TelegramCredential(Base):
    __tablename__ = "telegram_credentials"

    agent_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("ai_agents.agent_id", ondelete="CASCADE"),
        primary_key=True,
    )
    bot_token = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MarketplaceTemplate(Base):
    __tablename__ = "marketplace_templates"

    template_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    category = Column(PgEnum(TemplateCategory), nullable=False)
    description = Column(Text, nullable=True)
    spec_json = Column(JSONB, nullable=False)
    tags = Column(ARRAY(String), nullable=True)
    price_usd = Column(Integer, nullable=False, default=0)  # price in cents
    usage_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LLMProvider(Base):
    __tablename__ = "llm_providers"
    
    provider_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    provider_key = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    api_key_format = Column(String, nullable=True)
    base_url = Column(String, nullable=True)
    health_check_endpoint = Column(String, nullable=True)
    auth_header_format = Column(String, nullable=True)
    rate_limit_rpm = Column(Integer, nullable=True)
    rate_limit_tpm = Column(Integer, nullable=True)
    website = Column(String, nullable=True)
    pricing_url = Column(String, nullable=True)
    capabilities = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    models = relationship("LLMModel", back_populates="provider", cascade="all, delete-orphan")
    usage_logs = relationship("LLMUsageLog", back_populates="provider")


class LLMModel(Base):
    __tablename__ = "llm_models"
    
    model_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(PgUUID(as_uuid=True), ForeignKey("llm_providers.provider_id", ondelete="CASCADE"), nullable=False, index=True)
    model_key = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    model_family = Column(String, nullable=True, index=True)
    release_date = Column(Date, nullable=True)
    deprecation_date = Column(Date, nullable=True)
    max_output_tokens = Column(Integer, nullable=True)
    training_cutoff_date = Column(Date, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    context_length = Column(Integer, nullable=True)
    input_cost_per_1k = Column(DECIMAL(precision=10, scale=6), nullable=True)
    output_cost_per_1k = Column(DECIMAL(precision=10, scale=6), nullable=True)
    capabilities = Column(JSONB, nullable=True)
    is_recommended = Column(Boolean, nullable=False, server_default=text("false"))
    is_default = Column(Boolean, nullable=False, server_default=text("false"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    provider = relationship("LLMProvider", back_populates="models")
    usage_logs = relationship("LLMUsageLog", back_populates="model")
    
    __table_args__ = (
        UniqueConstraint("provider_id", "model_key", name="uq_provider_model_key"),
    )


class LLMUsageLog(Base):
    __tablename__ = "llm_usage_logs"
    
    usage_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_id = Column(PgUUID(as_uuid=True), ForeignKey("llm_providers.provider_id", ondelete="SET NULL"), nullable=True, index=True)
    model_id = Column(PgUUID(as_uuid=True), ForeignKey("llm_models.model_id", ondelete="SET NULL"), nullable=True, index=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_cost = Column(DECIMAL(precision=10, scale=6), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    status = Column(String, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    user = relationship("User")
    provider = relationship("LLMProvider", back_populates="usage_logs")
    model = relationship("LLMModel", back_populates="usage_logs")


# —————————————————————————————————————————————————————
#  Auth Policy Models - Dynamic Auth Configuration
# —————————————————————————————————————————————————————


class AuthPolicy(Base):
    __tablename__ = "auth_policies"
    
    id = Column(Integer, primary_key=True)
    service_id = Column(String(100), nullable=True, unique=True, index=True)
    provider = Column(String(50), nullable=False, index=True)  # Mantener para compatibilidad
    service = Column(String(50), nullable=True, index=True)    # Mantener para compatibilidad
    mechanism = Column(String(50), nullable=False, index=True)
    base_auth_url = Column(String(200), nullable=False)
    max_scopes = Column(JSONB, nullable=True)
    auth_config = Column(JSONB, nullable=True)
    display_name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Generated column for backward compatibility
    auth_string = Column(
        String(100),
        Computed(
            "CASE WHEN service IS NOT NULL THEN CONCAT(mechanism, '_', provider, '_', service) "
            "ELSE CONCAT(mechanism, '_', provider) END"
        ),
        nullable=True,
        index=True
    )
    
    # Relationships
    action_auth_scopes = relationship("ActionAuthScope", back_populates="auth_policy", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("provider", "service", "mechanism", name="uq_auth_policies_provider_service_mechanism"),
        Index("idx_auth_policies_provider_service", "provider", "service"),
    )


class ActionAuthScope(Base):
    __tablename__ = "action_auth_scopes"
    
    id = Column(Integer, primary_key=True)
    action_id = Column(PgUUID(as_uuid=True), ForeignKey("actions.action_id", ondelete="CASCADE"), nullable=False, index=True)
    auth_policy_id = Column(Integer, ForeignKey("auth_policies.id", ondelete="CASCADE"), nullable=False, index=True)
    required_scopes = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # TODO: Generated column for debugging and compatibility (disabled for now)
    # auth_string = Column(
    #     String(150),
    #     Computed(
    #         "(SELECT CASE "
    #         "WHEN ap.service IS NOT NULL THEN CONCAT(ap.mechanism, '_', ap.provider, '_', ap.service, '_action_', action_id::text) "
    #         "ELSE CONCAT(ap.mechanism, '_', ap.provider, '_action_', action_id::text) "
    #         "END FROM auth_policies ap WHERE ap.id = auth_policy_id)"
    #     ),
    #     nullable=True
    # )
    
    # Relationships
    action = relationship("Action")
    auth_policy = relationship("AuthPolicy", back_populates="action_auth_scopes")
    
    __table_args__ = (
        UniqueConstraint("action_id", name="uq_action_auth_scopes_action"),
    )


# —————————————————————————————————————————————————————
#  Page Customization Models
# —————————————————————————————————————————————————————

class PageTemplate(Base):
    """
    Modelo para almacenar templates de página personalizados por agente
    """
    __tablename__ = "page_templates"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(PgUUID(as_uuid=True), ForeignKey("ai_agents.agent_id", ondelete="CASCADE"), nullable=False, index=True)
    template_name = Column(String(100), nullable=False, default="default")
    
    # Template content
    html_content = Column(Text, nullable=True)
    css_content = Column(Text, nullable=True)
    js_content = Column(Text, nullable=True)
    
    # Metadata
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)
    
    # Customization history
    customization_prompt = Column(Text, nullable=True)  # Original user prompt
    applied_changes = Column(JSONB, nullable=True)  # JSON of applied changes
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    agent = relationship("AIAgent")
    
    __table_args__ = (
        UniqueConstraint("agent_id", "template_name", "version", name="uq_page_templates_agent_name_version"),
        Index("idx_page_templates_agent_active", "agent_id", "is_active"),
    )


class UserTokenUsage(Base):
    """
    Tracking de tokens consumidos por workflow/execution para analytics y costos
    """
    __tablename__ = "user_token_usage"
    
    usage_id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(PgUUID(as_uuid=True), ForeignKey("flows.flow_id", ondelete="CASCADE"), nullable=True, index=True)
    execution_id = Column(PgUUID(as_uuid=True), ForeignKey("flow_executions.execution_id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Tokens consumidos
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, Computed("input_tokens + output_tokens"), nullable=False)
    
    # Costos calculados (GPT-4.1: $2/1M input, $8/1M output)
    input_cost = Column(DECIMAL(precision=10, scale=6), nullable=False, default=0)
    output_cost = Column(DECIMAL(precision=10, scale=6), nullable=False, default=0)
    total_cost = Column(DECIMAL(precision=10, scale=6), Computed("input_cost + output_cost"), nullable=False)
    
    # Metadata
    model_used = Column(String(50), nullable=False, default="gpt-4.1")
    operation_type = Column(String(50), nullable=True)  # "workflow", "chat", "ai_agent"
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    workflow = relationship("Flow", foreign_keys=[workflow_id])
    execution = relationship("FlowExecution", foreign_keys=[execution_id])
    
    __table_args__ = (
        Index("idx_user_token_usage_user_month", "user_id", "created_at"),
        Index("idx_user_token_usage_workflow", "workflow_id", "created_at"),
    )


class UserSubscription(Base):
    """
    Límites y uso de tokens por usuario, similar al sistema de Claude
    """
    __tablename__ = "user_subscriptions"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # Plan configuration
    plan_type = Column(String(20), nullable=False, default="basic")  # basic, pro, enterprise
    monthly_token_limit = Column(Integer, nullable=False, default=200000)
    tokens_used_current_month = Column(Integer, nullable=False, default=0)
    
    # Billing cycle
    billing_cycle_start = Column(Date, nullable=False, default=func.current_date())
    next_reset_date = Column(Date, nullable=False, default=func.current_date() + text("INTERVAL '1 month'"))
    
    # Usage alerts
    alert_80_sent = Column(Boolean, nullable=False, default=False)
    alert_90_sent = Column(Boolean, nullable=False, default=False) 
    limit_reached = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    # Helper properties
    @property
    def usage_percentage(self) -> float:
        """Porcentaje de uso actual del límite mensual"""
        if self.monthly_token_limit == 0:
            return 0.0
        return (self.tokens_used_current_month / self.monthly_token_limit) * 100
    
    @property  
    def remaining_tokens(self) -> int:
        """Tokens restantes en el período actual"""
        return max(0, self.monthly_token_limit - self.tokens_used_current_month)
    
    @property
    def is_over_limit(self) -> bool:
        """Si el usuario superó su límite mensual"""
        return self.tokens_used_current_month >= self.monthly_token_limit
