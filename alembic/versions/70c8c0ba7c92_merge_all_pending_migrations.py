"""merge all pending migrations

Revision ID: 70c8c0ba7c92
Revises: 20250613_ai_agent_llm_ref, ab702a20fc25
Create Date: 2025-06-14 19:10:52.960168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70c8c0ba7c92'
down_revision: Union[str, None] = ('20250613_ai_agent_llm_ref', 'ab702a20fc25')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
