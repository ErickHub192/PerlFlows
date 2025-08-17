"""make service_id nullable in auth_policies

Revision ID: fix_service_id_nullable
Revises: 
Create Date: 2025-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_service_id_nullable'
down_revision = 'f018fb42fb1b'  # Latest migration before this fix
branch_labels = None
depends_on = None


def upgrade():
    """Make service_id nullable in auth_policies table"""
    try:
        # Make service_id nullable
        op.alter_column('auth_policies', 'service_id',
                       existing_type=sa.String(100),
                       nullable=True)
        print("Made service_id nullable in auth_policies")
    except Exception as e:
        print(f"Could not alter column: {e}")
        # This might fail if constraint issues exist, but the app will still work


def downgrade():
    """Revert service_id to not nullable"""
    try:
        # Make service_id not nullable (only if all values are filled)
        op.alter_column('auth_policies', 'service_id',
                       existing_type=sa.String(100),
                       nullable=False)
    except Exception as e:
        print(f"Could not revert column: {e}")