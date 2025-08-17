"""add service_id to oauth_states

Revision ID: 20250706_add_service_id_to_oauth_states
Revises: kill_flavors_migration
Create Date: 2025-07-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_service_id_oauth'
down_revision: Union[str, None] = 'kill_flavors'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add service_id column to oauth_states table for agnostic OAuth flow."""
    
    # Add service_id column
    op.add_column('oauth_states', sa.Column('service_id', sa.String(), nullable=True))
    
    # Update existing records with default service_id based on provider
    op.execute("""
        UPDATE oauth_states 
        SET service_id = CASE 
            WHEN provider = 'google' THEN 'gmail'
            WHEN provider = 'microsoft' THEN 'outlook'
            WHEN provider = 'slack' THEN 'slack'
            WHEN provider = 'github' THEN 'github'
            ELSE provider
        END
        WHERE service_id IS NULL
    """)
    
    # Make service_id NOT NULL
    op.alter_column('oauth_states', 'service_id', nullable=False)
    
    # Drop old unique constraint
    op.drop_constraint('uq_oauth_states_user_provider', 'oauth_states', type_='unique')
    
    # Add new unique constraint including service_id
    op.create_unique_constraint(
        'uq_oauth_states_user_provider_service', 
        'oauth_states', 
        ['user_id', 'provider', 'service_id']
    )


def downgrade() -> None:
    """Remove service_id column from oauth_states table."""
    
    # Drop new unique constraint
    op.drop_constraint('uq_oauth_states_user_provider_service', 'oauth_states', type_='unique')
    
    # Restore old unique constraint
    op.create_unique_constraint(
        'uq_oauth_states_user_provider', 
        'oauth_states', 
        ['user_id', 'provider']
    )
    
    # Drop service_id column
    op.drop_column('oauth_states', 'service_id')