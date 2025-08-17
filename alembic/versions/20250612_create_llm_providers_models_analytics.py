"""create llm providers models and analytics tables

Revision ID: 20250612_llm_providers
Revises: 20250611_create_refresh_tokens_table
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250612_llm_providers'
down_revision = '20250611_create_refresh_tokens_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create llm_providers table
    op.create_table('llm_providers',
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider_key', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('api_key_format', sa.String(), nullable=True),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('health_check_endpoint', sa.String(), nullable=True),
        sa.Column('auth_header_format', sa.String(), nullable=True),
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=True),
        sa.Column('rate_limit_tpm', sa.Integer(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('pricing_url', sa.String(), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('provider_id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('provider_key')
    )
    
    # Create index on provider_key for fast lookups
    op.create_index('ix_llm_providers_provider_key', 'llm_providers', ['provider_key'])
    op.create_index('ix_llm_providers_is_active', 'llm_providers', ['is_active'])

    # Create llm_models table
    op.create_table('llm_models',
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_key', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model_family', sa.String(), nullable=True),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('deprecation_date', sa.Date(), nullable=True),
        sa.Column('max_output_tokens', sa.Integer(), nullable=True),
        sa.Column('training_cutoff_date', sa.Date(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('context_length', sa.Integer(), nullable=True),
        sa.Column('input_cost_per_1k', sa.DECIMAL(precision=10, scale=6), nullable=True),
        sa.Column('output_cost_per_1k', sa.DECIMAL(precision=10, scale=6), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_recommended', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.provider_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('model_id'),
        sa.UniqueConstraint('provider_id', 'model_key', name='uq_provider_model_key')
    )
    
    # Create indexes on llm_models
    op.create_index('ix_llm_models_provider_id', 'llm_models', ['provider_id'])
    op.create_index('ix_llm_models_model_key', 'llm_models', ['model_key'])
    op.create_index('ix_llm_models_is_active', 'llm_models', ['is_active'])
    op.create_index('ix_llm_models_is_recommended', 'llm_models', ['is_recommended'])
    op.create_index('ix_llm_models_model_family', 'llm_models', ['model_family'])

    # Create llm_usage_logs table
    op.create_table('llm_usage_logs',
        sa.Column('usage_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.DECIMAL(precision=10, scale=6), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.provider_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_id'], ['llm_models.model_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('usage_id')
    )
    
    # Create indexes for analytics queries
    op.create_index('ix_usage_user_date', 'llm_usage_logs', ['user_id', 'created_at'])
    op.create_index('ix_usage_provider_date', 'llm_usage_logs', ['provider_id', 'created_at'])
    op.create_index('ix_usage_model_date', 'llm_usage_logs', ['model_id', 'created_at'])
    op.create_index('ix_usage_status', 'llm_usage_logs', ['status'])

    # Insert initial data for OpenAI
    op.execute("""
        INSERT INTO llm_providers (name, provider_key, description, api_key_format, base_url, health_check_endpoint, auth_header_format, rate_limit_rpm, rate_limit_tpm, website, pricing_url, capabilities) VALUES 
        ('OpenAI', 'openai', 'GPT models family - most popular and widely used LLMs', 'sk-...', 'https://api.openai.com/v1', '/models', 'Bearer {api_key}', 3500, 90000, 'https://openai.com', 'https://openai.com/pricing', '["text_generation", "code_generation", "chat_conversation", "function_calling", "json_mode", "vision_understanding"]')
    """)

    # Insert initial data for Anthropic
    op.execute("""
        INSERT INTO llm_providers (name, provider_key, description, api_key_format, base_url, health_check_endpoint, auth_header_format, rate_limit_rpm, rate_limit_tpm, website, pricing_url, capabilities) VALUES 
        ('Anthropic', 'anthropic', 'Claude 3 family - advanced reasoning with large context windows', 'sk-ant-...', 'https://api.anthropic.com', '/v1/messages', 'x-api-key: {api_key}', 1000, 200000, 'https://anthropic.com', 'https://docs.anthropic.com/claude/docs/models-overview', '["text_generation", "code_generation", "chat_conversation", "vision_understanding", "large_context", "constitutional_ai"]')
    """)

    # Get provider IDs for model insertion
    openai_provider_result = op.get_bind().execute(sa.text("SELECT provider_id FROM llm_providers WHERE provider_key = 'openai'"))
    openai_provider_id = openai_provider_result.fetchone()[0]

    anthropic_provider_result = op.get_bind().execute(sa.text("SELECT provider_id FROM llm_providers WHERE provider_key = 'anthropic'"))
    anthropic_provider_id = anthropic_provider_result.fetchone()[0]

    # Insert OpenAI models
    op.execute(f"""
        INSERT INTO llm_models (provider_id, model_key, display_name, description, model_family, release_date, context_length, max_output_tokens, input_cost_per_1k, output_cost_per_1k, capabilities, is_recommended, is_default, response_time_ms) VALUES 
        ('{openai_provider_id}', 'gpt-4', 'GPT-4', 'Most capable model, best for complex reasoning tasks', 'gpt-4', '2023-03-14', 8192, 4096, 0.030000, 0.060000, '["text_generation", "code_generation", "chat_conversation", "function_calling"]', true, true, 3000),
        ('{openai_provider_id}', 'gpt-4-turbo', 'GPT-4 Turbo', 'Latest GPT-4 with 128K context and lower cost', 'gpt-4', '2024-04-09', 128000, 4096, 0.010000, 0.030000, '["text_generation", "code_generation", "chat_conversation", "function_calling", "vision_understanding"]', true, false, 2500),
        ('{openai_provider_id}', 'gpt-4-turbo-preview', 'GPT-4 Turbo Preview', 'Preview version with latest features', 'gpt-4', '2024-01-25', 128000, 4096, 0.010000, 0.030000, '["text_generation", "code_generation", "chat_conversation", "function_calling"]', false, false, 2800),
        ('{openai_provider_id}', 'gpt-3.5-turbo', 'GPT-3.5 Turbo', 'Fast and cost-effective for simpler tasks', 'gpt-3.5', '2023-03-01', 16385, 4096, 0.001000, 0.002000, '["text_generation", "code_generation", "chat_conversation", "function_calling"]', true, false, 1500),
        ('{openai_provider_id}', 'gpt-3.5-turbo-16k', 'GPT-3.5 Turbo 16K', 'GPT-3.5 with larger context window', 'gpt-3.5', '2023-06-13', 16385, 4096, 0.003000, 0.004000, '["text_generation", "code_generation", "chat_conversation", "function_calling"]', false, false, 1600)
    """)

    # Insert Anthropic models
    op.execute(f"""
        INSERT INTO llm_models (provider_id, model_key, display_name, description, model_family, release_date, context_length, max_output_tokens, input_cost_per_1k, output_cost_per_1k, capabilities, is_recommended, is_default, response_time_ms) VALUES 
        ('{anthropic_provider_id}', 'claude-3-sonnet-20240229', 'Claude 3 Sonnet', 'Balanced performance and speed - recommended for most tasks', 'claude-3', '2024-02-29', 200000, 4096, 0.003000, 0.015000, '["text_generation", "code_generation", "chat_conversation", "vision_understanding"]', true, true, 2000),
        ('{anthropic_provider_id}', 'claude-3-opus-20240229', 'Claude 3 Opus', 'Most powerful Claude model for complex reasoning', 'claude-3', '2024-02-29', 200000, 4096, 0.015000, 0.075000, '["text_generation", "code_generation", "chat_conversation", "vision_understanding"]', true, false, 4000),
        ('{anthropic_provider_id}', 'claude-3-haiku-20240307', 'Claude 3 Haiku', 'Fastest Claude model for simple tasks and quick responses', 'claude-3', '2024-03-07', 200000, 4096, 0.000250, 0.001250, '["text_generation", "code_generation", "chat_conversation"]', true, false, 800)
    """)


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('llm_usage_logs')
    op.drop_table('llm_models')
    op.drop_table('llm_providers')