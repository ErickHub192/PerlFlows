"""Add service_id to auth_policies

Revision ID: auth_policies_service_id
Revises: cleanup_redundant
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'auth_policies_service_id'
down_revision = 'cleanup_redundant'
branch_labels = None
depends_on = None

def upgrade():
    """Agregar service_id a auth_policies y migrar datos"""
    
    # 1. Agregar columna service_id
    op.add_column('auth_policies', sa.Column('service_id', sa.String(100), nullable=True))
    
    # 2. Migrar datos existentes provider+service → service_id
    op.execute("""
        UPDATE auth_policies SET service_id = 
        CASE 
            -- Google services
            WHEN provider = 'google' AND service = 'gmail' THEN 'gmail'
            WHEN provider = 'google' AND service = 'sheets' THEN 'google_sheets'
            WHEN provider = 'google' AND service = 'drive' THEN 'google_drive'
            WHEN provider = 'google' AND service = 'calendar' THEN 'google_calendar'
            
            -- Microsoft services  
            WHEN provider = 'microsoft' AND service = 'outlook' THEN 'outlook'
            WHEN provider = 'microsoft' AND service = 'teams' THEN 'teams'
            WHEN provider = 'microsoft' AND service = 'calendar' THEN 'outlook_calendar'
            
            -- Services without service field (service IS NULL or empty)
            WHEN provider = 'slack' THEN 'slack'
            WHEN provider = 'telegram' THEN 'telegram'
            WHEN provider = 'dropbox' THEN 'dropbox'
            WHEN provider = 'salesforce' THEN 'salesforce'
            WHEN provider = 'hubspot' THEN 'hubspot'
            WHEN provider = 'whatsapp' THEN 'whatsapp'
            WHEN provider = 'stripe' THEN 'stripe'
            WHEN provider = 'airtable' THEN 'airtable'
            WHEN provider = 'ai' THEN 'ai'
            
            -- Database services
            WHEN provider = 'postgres' THEN 'postgres'
            WHEN provider = 'mysql' THEN 'mysql'
            WHEN provider = 'mongo' THEN 'mongo'
            WHEN provider = 'redis' THEN 'redis'
            WHEN provider = 'sqlite' THEN 'sqlite'
            
            -- Fallback: combine provider_service or just provider
            WHEN service IS NOT NULL AND service != '' AND service != provider THEN 
                CONCAT(provider, '_', service)
            ELSE provider
        END
        WHERE service_id IS NULL;
    """)
    
    # 3. Hacer service_id obligatorio y único
    op.alter_column('auth_policies', 'service_id', nullable=False)
    op.create_unique_constraint('uq_auth_policies_service_id', 'auth_policies', ['service_id'])
    op.create_index('idx_auth_policies_service_id', 'auth_policies', ['service_id'])
    
    print("Migration completed: auth_policies now uses service_id")

def downgrade():
    """Rollback: eliminar service_id"""
    op.drop_constraint('uq_auth_policies_service_id', 'auth_policies', type_='unique')
    op.drop_index('idx_auth_policies_service_id', 'auth_policies')
    op.drop_column('auth_policies', 'service_id')