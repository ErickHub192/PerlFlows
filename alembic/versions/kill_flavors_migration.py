"""Kill flavors - migrate to service_id only

Revision ID: kill_flavors
Revises: 
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'kill_flavors'
down_revision = 'c161a6666cf9'  # último migration
branch_labels = None
depends_on = None

def upgrade():
    """Eliminar flavors y migrar a service_id únicamente"""
    
    # 1. Añadir columna service_id si no existe
    op.add_column('credentials', sa.Column('service_id', sa.String(100), nullable=True))
    
    # 2. Migrar datos existentes: provider + flavor -> service_id
    op.execute("""
        UPDATE credentials SET service_id = 
        CASE 
            -- Google services
            WHEN provider = 'google' AND flavor = 'gmail' THEN 'gmail'
            WHEN provider = 'google' AND flavor = 'sheets' THEN 'google_sheets'
            WHEN provider = 'google' AND flavor = 'drive' THEN 'google_drive'
            WHEN provider = 'google' AND flavor = 'calendar' THEN 'google_calendar'
            
            -- Microsoft services  
            WHEN provider = 'microsoft' AND flavor = 'outlook' THEN 'outlook'
            WHEN provider = 'microsoft' AND flavor = 'teams' THEN 'teams'
            WHEN provider = 'microsoft' AND flavor = 'calendar' THEN 'outlook_calendar'
            
            -- Services without flavor (flavor IS NULL or empty)
            WHEN provider = 'slack' THEN 'slack'
            WHEN provider = 'telegram' THEN 'telegram'
            WHEN provider = 'dropbox' THEN 'dropbox'
            WHEN provider = 'salesforce' THEN 'salesforce'
            WHEN provider = 'hubspot' THEN 'hubspot'
            WHEN provider = 'whatsapp' THEN 'whatsapp'
            WHEN provider = 'stripe' THEN 'stripe'
            WHEN provider = 'airtable' THEN 'airtable'
            
            -- Database services
            WHEN provider = 'postgres' THEN 'postgres'
            WHEN provider = 'mysql' THEN 'mysql'
            WHEN provider = 'mongo' THEN 'mongo'
            WHEN provider = 'redis' THEN 'redis'
            WHEN provider = 'sqlite' THEN 'sqlite'
            
            -- API Key services
            WHEN provider = 'ai' THEN 'ai'
            
            -- Fallback: use provider if no specific mapping
            ELSE provider
        END
        WHERE service_id IS NULL;
    """)
    
    # 3. Hacer service_id obligatorio
    op.alter_column('credentials', 'service_id', nullable=False)
    
    # 4. Eliminar constraint único viejo y crear nuevo
    op.drop_constraint('uq_user_provider_flavor_chat', 'credentials', type_='unique')
    op.create_unique_constraint('uq_user_service_chat', 'credentials', ['user_id', 'service_id', 'chat_id'])
    
    # 5. Eliminar columnas obsoletas
    op.drop_column('credentials', 'flavor')
    op.drop_column('credentials', 'provider')
    
    print("Migration completed: Flavors eliminated, service_id is now the single source of truth")

def downgrade():
    """Rollback: restaurar provider + flavor"""
    
    # Add back provider and flavor columns
    op.add_column('credentials', sa.Column('provider', sa.String(50), nullable=True))
    op.add_column('credentials', sa.Column('flavor', sa.String(50), nullable=True))
    
    # Migrate service_id back to provider + flavor
    op.execute("""
        UPDATE credentials SET 
            provider = CASE
                WHEN service_id = 'gmail' THEN 'google'
                WHEN service_id = 'google_sheets' THEN 'google'
                WHEN service_id = 'google_drive' THEN 'google'
                WHEN service_id = 'google_calendar' THEN 'google'
                WHEN service_id = 'outlook' THEN 'microsoft'
                WHEN service_id = 'teams' THEN 'microsoft'
                WHEN service_id = 'outlook_calendar' THEN 'microsoft'
                ELSE service_id
            END,
            flavor = CASE
                WHEN service_id = 'gmail' THEN 'gmail'
                WHEN service_id = 'google_sheets' THEN 'sheets'
                WHEN service_id = 'google_drive' THEN 'drive'
                WHEN service_id = 'google_calendar' THEN 'calendar'
                WHEN service_id = 'outlook' THEN 'outlook'
                WHEN service_id = 'teams' THEN 'teams'
                WHEN service_id = 'outlook_calendar' THEN 'calendar'
                ELSE NULL
            END;
    """)
    
    # Restore old constraint
    op.drop_constraint('uq_user_service_chat', 'credentials', type_='unique')
    op.create_unique_constraint('uq_user_provider_flavor_chat', 'credentials', ['user_id', 'provider', 'flavor', 'chat_id'])
    
    # Remove service_id column
    op.drop_column('credentials', 'service_id')