"""create agent_runs table

Revision ID: 20250610_agent_runs
Revises:      20250609_agent_memories
Create Date:  2025-06-10 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250610_agent_runs"
down_revision: Union[str, None] = "20250609_agent_memories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # IMPORTANTE: el ENUM "agentstatus" ya fue creado en 20250608_extend_agents.py.
    # Aquí lo referenciamos, SIN volver a crearlo: definimos los mismos valores
    # pero con create_type=False para que SQLAlchemy use el ENUM ya existente.
    # ------------------------------------------------------------------

    # Definimos status_enum referenciando el tipo preexistente:
    status_enum = sa.Enum(
        "queued", "running", "paused", "succeeded", "failed",
        name="agentstatus",
        create_type=False
    )

    op.create_table(
        "agent_runs",
        sa.Column(
            "run_id",
            postgresql.UUID(),        # UUID para el ID de la corrida
            primary_key=True,
            nullable=False
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(),
            nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False
        ),
        sa.Column(
            "status",
            status_enum,              # usamos el ENUM existente
            nullable=False,
            server_default="queued"
        ),
        sa.Column(
            "goal",
            sa.Text(),
            nullable=True
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        ),
        sa.Column(
            "error",
            sa.Text(),
            nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["ai_agents.agent_id"], ondelete="CASCADE"
        ),
    )

    # Índice para acelerar consultas por agent_id
    op.create_index(
        "ix_agent_runs_agent_id",
        "agent_runs",
        ["agent_id"],
        unique=False
    )


def downgrade() -> None:
    # Al hacer downgrade solo borramos la tabla y el índice.
    # NO tocamos el ENUM "agentstatus", ya que sigue en uso por ai_agents.
    op.drop_index("ix_agent_runs_agent_id", table_name="agent_runs")
    op.drop_table("agent_runs")
