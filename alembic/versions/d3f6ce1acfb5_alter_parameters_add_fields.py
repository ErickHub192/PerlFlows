"""alter_parameters_add_fields

Revision ID: d3f6ce1acfb5
Revises: c7c00ad6e88e
Create Date: 2025-04-18 15:33:06.669757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f6ce1acfb5'
down_revision: Union[str, None] = 'c7c00ad6e88e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('parameters', sa.Column('field_type', sa.String(), nullable=True))
    op.add_column('parameters', sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('parameters', sa.Column('example', sa.Text(), nullable=True))
    op.add_column('parameters', sa.Column('is_secret', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('parameters', 'is_secret')
    op.drop_column('parameters', 'example')
    op.drop_column('parameters', 'required')
    op.drop_column('parameters', 'field_type')
