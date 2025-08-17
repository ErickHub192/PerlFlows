"""add oauth config columns to credentials

Revision ID: add_oauth_config
Revises: f97cd0337417
Create Date: 2025-07-06 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_oauth_config'
down_revision: Union[str, None] = 'f97cd0337417'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OAuth configuration columns to credentials table for future user-provided credentials"""
    
    # Add provider column (google, microsoft, slack, etc.)
    op.add_column('credentials', sa.Column('provider', sa.String(50), nullable=True))
    
    # Add client_id and client_secret for user-provided OAuth credentials
    op.add_column('credentials', sa.Column('client_id', sa.String(255), nullable=True))
    op.add_column('credentials', sa.Column('client_secret', sa.LargeBinary, nullable=True))  # Encrypted like tokens
    
    # Update existing records to set provider based on service_id patterns
    op.execute("""
        UPDATE credentials 
        SET provider = CASE 
            WHEN service_id IN ('gmail', 'google_calendar', 'google_drive', 'google_sheets') THEN 'google'
            WHEN service_id = 'outlook' THEN 'microsoft'
            WHEN service_id = 'dropbox' THEN 'dropbox'
            WHEN service_id = 'slack' THEN 'slack'
            WHEN service_id = 'salesforce' THEN 'salesforce'
            WHEN service_id = 'github' THEN 'github'
            ELSE service_id
        END
        WHERE provider IS NULL
    """)


def downgrade() -> None:
    """Remove OAuth configuration columns from credentials table"""
    
    # Drop the added columns
    op.drop_column('credentials', 'client_secret')
    op.drop_column('credentials', 'client_id')
    op.drop_column('credentials', 'provider')