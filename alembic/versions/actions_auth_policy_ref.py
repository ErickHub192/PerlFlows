"""Add auth_policy_id reference to actions

Revision ID: actions_auth_policy_ref
Revises: auth_policies_service_id
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'actions_auth_policy_ref'
down_revision = 'auth_policies_service_id'
branch_labels = None
depends_on = None

def upgrade():
    """Agregar referencia directa de actions a auth_policies"""
    
    # 1. Agregar columnas para auto-trigger auth
    op.add_column('actions', sa.Column('auth_policy_id', sa.Integer(), nullable=True))
    op.add_column('actions', sa.Column('auth_required', sa.Boolean(), nullable=True))
    op.add_column('actions', sa.Column('custom_scopes', sa.ARRAY(sa.String()), nullable=True))
    
    # Establecer default para auth_required
    op.execute("UPDATE actions SET auth_required = FALSE WHERE auth_required IS NULL")
    op.alter_column('actions', 'auth_required', nullable=False)
    
    # 2. Crear foreign key constraint
    op.create_foreign_key(
        'fk_actions_auth_policy',
        'actions', 'auth_policies',
        ['auth_policy_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # 3. Crear índices para performance
    op.create_index('idx_actions_auth_policy_id', 'actions', ['auth_policy_id'])
    op.create_index('idx_actions_auth_required', 'actions', ['auth_required'])
    
    # 4. Migrar datos existentes desde nodes.default_auth → actions.auth_policy_id
    op.execute("""
        UPDATE actions 
        SET 
            auth_policy_id = ap.id,
            auth_required = (n.default_auth IS NOT NULL AND n.default_auth != '')
        FROM nodes n, auth_policies ap
        WHERE 
            actions.node_id = n.node_id
            AND n.default_auth IS NOT NULL 
            AND n.default_auth != ''
            AND (
                -- Mapeo de default_auth string a service_id
                (n.default_auth LIKE 'oauth2_%' AND ap.service_id = SUBSTRING(n.default_auth FROM 8))
                OR
                (n.default_auth LIKE 'api_key_%' AND ap.service_id = SUBSTRING(n.default_auth FROM 9))
                OR
                (n.default_auth LIKE 'bot_token_%' AND ap.service_id = SUBSTRING(n.default_auth FROM 11))
                OR
                -- Mapeo directo si default_auth es el service_id
                (ap.service_id = n.default_auth)
            );
    """)
    
    print("Migration completed: actions now have direct auth_policy reference")

def downgrade():
    """Rollback: eliminar referencias auth"""
    op.drop_index('idx_actions_auth_required', 'actions')
    op.drop_index('idx_actions_auth_policy_id', 'actions')
    op.drop_constraint('fk_actions_auth_policy', 'actions', type_='foreignkey')
    op.drop_column('actions', 'custom_scopes')
    op.drop_column('actions', 'auth_required')
    op.drop_column('actions', 'auth_policy_id')