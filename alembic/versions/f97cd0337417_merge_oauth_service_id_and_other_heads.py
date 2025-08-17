"""merge oauth service_id and other heads

Revision ID: f97cd0337417
Revises: 20250706_add_service_id_to_oauth_states, 88a4dd299c9f
Create Date: 2025-07-05 18:50:13.033771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f97cd0337417'
down_revision: Union[str, None] = ('add_service_id_oauth', '88a4dd299c9f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
