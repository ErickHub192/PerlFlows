"""enhance marketplace templates

Revision ID: 20250609_enhance_marketplace_templates
Revises: 20250607_usage_mode
Create Date: 2025-06-09 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250609_enhance_marketplace_templates'
down_revision = '20250607_usage_mode'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum for template categories
    template_category_enum = postgresql.ENUM(
        'business_sales',
        'finance_accounting', 
        'customer_service',
        'marketing_content',
        'ecommerce_retail',
        'mexico_latam',
        'development_devops',
        name='templatecategory'
    )
    template_category_enum.create(op.get_bind())
    
    # Add new columns to marketplace_templates
    op.add_column('marketplace_templates', sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True))
    op.add_column('marketplace_templates', sa.Column('price_usd', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('marketplace_templates', sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('marketplace_templates', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Update category column to use enum
    op.execute("ALTER TABLE marketplace_templates ALTER COLUMN category DROP DEFAULT")
    op.execute("ALTER TABLE marketplace_templates ALTER COLUMN category TYPE templatecategory USING category::templatecategory")
    op.alter_column('marketplace_templates', 'category', nullable=False)


def downgrade() -> None:
    # Revert category column changes
    op.alter_column('marketplace_templates', 'category', nullable=True)
    op.execute("ALTER TABLE marketplace_templates ALTER COLUMN category TYPE varchar")
    
    # Drop added columns
    op.drop_column('marketplace_templates', 'is_active')
    op.drop_column('marketplace_templates', 'usage_count')
    op.drop_column('marketplace_templates', 'price_usd')
    op.drop_column('marketplace_templates', 'tags')
    
    # Drop enum
    op.execute("DROP TYPE templatecategory")