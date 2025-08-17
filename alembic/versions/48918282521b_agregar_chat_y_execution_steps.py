"""Agregar chat y execution steps

Revision ID: 48918282521b
Revises: c344ae30248d
Create Date: 2025-05-24 22:32:57.240075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '48918282521b'
down_revision: Union[str, None] = 'c344ae30248d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # — tablas nuevas —
    op.create_table(
        'chat_sessions',
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'], unique=False)

    op.create_table(
        'chat_messages',
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'], unique=False)

    op.create_table(
        'flow_execution_steps',
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('node_id', sa.UUID(), nullable=False),
        sa.Column('action_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['flow_executions.execution_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('step_id')
    )

    # — ajustes en tablas existentes —

    # actions: rename is_trigger → action_type
    with op.batch_alter_table('actions') as batch_op:
        batch_op.add_column(sa.Column('action_type', sa.Enum('Trigger', 'Action', name='action_type'), server_default='Action', nullable=False))
        batch_op.drop_column('is_trigger')

    # agent_memories: enforce NOT NULL on metadatas
    with op.batch_alter_table('agent_memories') as batch_op:
        batch_op.alter_column(
            'metadatas',
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            nullable=False
        )

    # credentials: TEXT → BYTEA con casteo
    with op.batch_alter_table('credentials') as batch_op:
        batch_op.alter_column(
            'access_token',
            existing_type=sa.TEXT(),
            type_=sa.LargeBinary(),
            postgresql_using="access_token::bytea",
            existing_nullable=True
        )
        batch_op.alter_column(
            'refresh_token',
            existing_type=sa.TEXT(),
            type_=sa.LargeBinary(),
            postgresql_using="refresh_token::bytea",
            existing_nullable=True
        )

    # flow_executions: índices
    op.create_index('ix_flow_executions_flow_id', 'flow_executions', ['flow_id'], unique=False)
    op.create_index('ix_flow_executions_status', 'flow_executions', ['status'], unique=False)

    # flows: add spec_version
    with op.batch_alter_table('flows') as batch_op:
        batch_op.add_column(sa.Column('spec_version', sa.Integer(), server_default=sa.text('1'), nullable=False))

    # nodes: add slug safely
    op.add_column('nodes', sa.Column('slug', sa.String(), nullable=True))
    op.execute(
        "UPDATE nodes "
        "SET slug = lower(regexp_replace(name, '[^a-zA-Z0-9]+', '_', 'g'))"
    )
    op.alter_column('nodes', 'slug', nullable=False)
    op.create_index('ix_nodes_slug', 'nodes', ['slug'], unique=False)

    # parameters: crear ENUM, quitar default, cambiar tipo con USING, reasignar default
    # 1) Crear tipo ENUM en DB
    param_type_enum = postgresql.ENUM('string', 'number', 'boolean', 'json', 'file', name='param_type')
    param_type_enum.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table('parameters') as batch_op:
        # 2) Eliminar el default antiguo para evitar conflictos
        batch_op.alter_column(
            'param_type',
            existing_type=sa.VARCHAR(),
            server_default=None
        )
        # 3) Cambiar tipo con USING
        batch_op.alter_column(
            'param_type',
            type_=param_type_enum,
            existing_nullable=False,
            postgresql_using="param_type::param_type"
        )
        # 4) Reasignar default en formato correcto para ENUM
        batch_op.alter_column(
            'param_type',
            existing_type=param_type_enum,
            server_default=sa.text("'string'::param_type"),
            existing_nullable=False
        )

    # triggers: unique constraint en job_id
    with op.batch_alter_table('triggers') as batch_op:
        batch_op.create_unique_constraint('uq_trigger_job_id', ['job_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # triggers
    with op.batch_alter_table('triggers') as batch_op:
        batch_op.drop_constraint('uq_trigger_job_id', type_='unique')

    # parameters: revertir cambios y eliminar ENUM
    with op.batch_alter_table('parameters') as batch_op:
        # quitar default ENUM
        batch_op.alter_column(
            'param_type',
            existing_type=postgresql.ENUM(name='param_type'),
            server_default=None
        )
        # devolver a VARCHAR
        batch_op.alter_column(
            'param_type',
            type_=sa.VARCHAR(),
            existing_nullable=False
        )
    postgresql.ENUM('string', 'number', 'boolean', 'json', 'file', name='param_type').drop(op.get_bind(), checkfirst=True)

    # nodes: eliminar índice y slug
    op.drop_index('ix_nodes_slug', table_name='nodes')
    op.drop_column('nodes', 'slug')

    # flows: eliminar spec_version
    with op.batch_alter_table('flows') as batch_op:
        batch_op.drop_column('spec_version')

    # flow_executions: eliminar índices
    op.drop_index('ix_flow_executions_status', table_name='flow_executions')
    op.drop_index('ix_flow_executions_flow_id', table_name='flow_executions')

    # credentials: BYTEA → TEXT
    with op.batch_alter_table('credentials') as batch_op:
        batch_op.alter_column(
            'refresh_token',
            existing_type=sa.LargeBinary(),
            type_=sa.TEXT(),
            existing_nullable=True
        )
        batch_op.alter_column(
            'access_token',
            existing_type=sa.LargeBinary(),
            type_=sa.TEXT(),
            existing_nullable=True
        )

    # agent_memories
    with op.batch_alter_table('agent_memories') as batch_op:
        batch_op.alter_column(
            'metadatas',
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )

    # actions: restaurar is_trigger, eliminar action_type
    with op.batch_alter_table('actions') as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_trigger',
                postgresql.ENUM('Trigger', 'Action', name='action_type'),
                server_default=sa.text("'Action'::action_type"),
                nullable=False
            )
        )
        batch_op.drop_column('action_type')

    # tablas nuevas
    op.drop_table('flow_execution_steps')
    op.drop_index('ix_chat_messages_session_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('ix_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_table('chat_sessions')
