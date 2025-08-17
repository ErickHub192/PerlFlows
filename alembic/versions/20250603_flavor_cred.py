"""Add flavor to credentials

Revision ID: 20250603_flavor_cred
Revises: 48918282521b
Create Date: 2025-06-03 17:31:57.005653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250603_flavor_cred'
down_revision: Union[str, None] = '48918282521b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('credentials', schema=None) as batch_op:
        batch_op.add_column(sa.Column('flavor', sa.String(), nullable=True))
        batch_op.drop_constraint(batch_op.f('uq_user_provider'), type_='unique')
        batch_op.create_index(batch_op.f('ix_credentials_flavor'), ['flavor'], unique=False)
        batch_op.create_unique_constraint(
            'uq_user_provider_flavor',
            ['user_id', 'provider', 'flavor']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('credentials', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_provider_flavor', type_='unique')
        batch_op.drop_index(batch_op.f('ix_credentials_flavor'))
        batch_op.create_unique_constraint(
            batch_op.f('uq_user_provider'),
            ['user_id', 'provider'],
            postgresql_nulls_not_distinct=False
        )
        batch_op.drop_column('flavor')
