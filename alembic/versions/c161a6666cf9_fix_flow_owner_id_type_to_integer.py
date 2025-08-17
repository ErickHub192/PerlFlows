"""fix_flow_owner_id_type_to_integer

Revision ID: c161a6666cf9
Revises: 1351d8abeb26
Create Date: 2025-06-20 23:08:21.219669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c161a6666cf9'
down_revision: Union[str, None] = '1351d8abeb26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix Flow.owner_id to be Integer instead of UUID for proper foreign key to users.id"""
    # Drop the existing owner_id column
    op.drop_column('flows', 'owner_id')
    
    # Add new owner_id column as Integer with foreign key
    op.add_column('flows', sa.Column('owner_id', sa.Integer, nullable=False))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_flows_owner_id_users',
        'flows', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for performance
    op.create_index('ix_flows_owner_id', 'flows', ['owner_id'])


def downgrade() -> None:
    """Revert Flow.owner_id back to UUID (for rollback purposes)"""
    # Drop foreign key constraint
    op.drop_constraint('fk_flows_owner_id_users', 'flows', type_='foreignkey')
    
    # Drop index
    op.drop_index('ix_flows_owner_id', 'flows')
    
    # Drop the Integer owner_id column
    op.drop_column('flows', 'owner_id')
    
    # Add back UUID owner_id column
    op.add_column('flows', sa.Column('owner_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False))
