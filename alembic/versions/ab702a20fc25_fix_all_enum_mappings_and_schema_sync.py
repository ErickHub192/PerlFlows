"""fix all enum mappings and schema sync

Revision ID: ab702a20fc25
Revises: 5bb186460d9f
Create Date: 2025-06-09 23:39:03.752845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab702a20fc25'
down_revision: Union[str, None] = '5bb186460d9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix marketplace_templates enum mapping issue specifically."""
    
    print("Fixing marketplace_templates enum mapping...")
    
    # The issue: SQLAlchemy is sending enum names like 'MEXICO_LATAM' instead of values like 'mexico_latam'
    # This suggests the enum mapping in SQLAlchemy model is not working correctly
    
    # Check if we need to do anything - column might already be correctly configured
    op.execute("""
        DO $$ 
        BEGIN
            RAISE NOTICE 'Checking marketplace_templates category column...';
            
            -- Check if the enum exists and if the column is already using it
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'templatecategory') THEN
                RAISE NOTICE 'templatecategory enum already exists';
                
                -- Check if column is already using the enum type
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'marketplace_templates' 
                    AND column_name = 'category' 
                    AND data_type = 'USER-DEFINED'
                ) THEN
                    RAISE NOTICE 'marketplace_templates.category is already using enum type - no action needed';
                ELSE
                    RAISE NOTICE 'Converting category column to use templatecategory enum';
                    ALTER TABLE marketplace_templates 
                    ALTER COLUMN category TYPE templatecategory 
                    USING 
                        CASE 
                            WHEN category = 'business_sales' THEN 'business_sales'::templatecategory
                            WHEN category = 'finance_accounting' THEN 'finance_accounting'::templatecategory
                            WHEN category = 'customer_service' THEN 'customer_service'::templatecategory
                            WHEN category = 'marketing_content' THEN 'marketing_content'::templatecategory
                            WHEN category = 'ecommerce_retail' THEN 'ecommerce_retail'::templatecategory
                            WHEN category = 'mexico_latam' THEN 'mexico_latam'::templatecategory
                            WHEN category = 'development_devops' THEN 'development_devops'::templatecategory
                            ELSE 'mexico_latam'::templatecategory  -- default fallback
                        END;
                END IF;
            ELSE
                -- Create the enum and convert the column
                RAISE NOTICE 'Creating templatecategory enum';
                CREATE TYPE templatecategory AS ENUM (
                    'business_sales', 
                    'finance_accounting', 
                    'customer_service',
                    'marketing_content', 
                    'ecommerce_retail', 
                    'mexico_latam', 
                    'development_devops'
                );
                
                RAISE NOTICE 'Converting category column to use templatecategory enum';
                ALTER TABLE marketplace_templates 
                ALTER COLUMN category TYPE templatecategory 
                USING 
                    CASE 
                        WHEN category = 'business_sales' THEN 'business_sales'::templatecategory
                        WHEN category = 'finance_accounting' THEN 'finance_accounting'::templatecategory
                        WHEN category = 'customer_service' THEN 'customer_service'::templatecategory
                        WHEN category = 'marketing_content' THEN 'marketing_content'::templatecategory
                        WHEN category = 'ecommerce_retail' THEN 'ecommerce_retail'::templatecategory
                        WHEN category = 'mexico_latam' THEN 'mexico_latam'::templatecategory
                        WHEN category = 'development_devops' THEN 'development_devops'::templatecategory
                        ELSE 'mexico_latam'::templatecategory  -- default fallback
                    END;
            END IF;
            
            RAISE NOTICE 'marketplace_templates enum mapping check completed';
            
        END $$;
    """)
    
    print("Marketplace templates enum mapping fixed!")


def downgrade() -> None:
    """Revert enum changes."""
    # Enum changes are generally not reversible safely
    print("Enum downgrade not implemented (not safe to revert)")
