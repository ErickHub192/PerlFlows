"""fix marketplace templates schema

Revision ID: 5bb186460d9f
Revises: bb87b8f50bdc
Create Date: 2025-06-09 23:24:09.347071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5bb186460d9f'
down_revision: Union[str, None] = 'bb87b8f50bdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to marketplace_templates table if they don't exist."""
    
    # Create enum if it doesn't exist
    templatecategory_enum = postgresql.ENUM(
        'business_sales',
        'finance_accounting', 
        'customer_service',
        'marketing_content',
        'ecommerce_retail',
        'mexico_latam',
        'development_devops',
        name='templatecategory'
    )
    
    # Check if enum exists, create if not
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE templatecategory AS ENUM (
                'business_sales',
                'finance_accounting', 
                'customer_service',
                'marketing_content',
                'ecommerce_retail',
                'mexico_latam',
                'development_devops'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add columns if they don't exist
    op.execute("""
        DO $$ BEGIN
            -- Add tags column
            BEGIN
                ALTER TABLE marketplace_templates ADD COLUMN tags VARCHAR[];
            EXCEPTION
                WHEN duplicate_column THEN null;
            END;
            
            -- Add price_usd column
            BEGIN
                ALTER TABLE marketplace_templates ADD COLUMN price_usd INTEGER NOT NULL DEFAULT 0;
            EXCEPTION
                WHEN duplicate_column THEN null;
            END;
            
            -- Add usage_count column
            BEGIN
                ALTER TABLE marketplace_templates ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0;
            EXCEPTION
                WHEN duplicate_column THEN null;
            END;
            
            -- Add is_active column
            BEGIN
                ALTER TABLE marketplace_templates ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
            EXCEPTION
                WHEN duplicate_column THEN null;
            END;
        END $$;
    """)
    
    # Update category column to use enum if it's still varchar
    op.execute("""
        DO $$ BEGIN
            -- Only alter if column is not already templatecategory type
            IF (SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'marketplace_templates' AND column_name = 'category') != 'USER-DEFINED' THEN
                ALTER TABLE marketplace_templates 
                ALTER COLUMN category TYPE templatecategory 
                USING category::templatecategory;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Revert changes."""
    # Remove added columns
    op.execute("""
        DO $$ BEGIN
            BEGIN
                ALTER TABLE marketplace_templates DROP COLUMN IF EXISTS tags;
            EXCEPTION
                WHEN others THEN null;
            END;
            
            BEGIN
                ALTER TABLE marketplace_templates DROP COLUMN IF EXISTS price_usd;
            EXCEPTION
                WHEN others THEN null;
            END;
            
            BEGIN
                ALTER TABLE marketplace_templates DROP COLUMN IF EXISTS usage_count;
            EXCEPTION
                WHEN others THEN null;
            END;
            
            BEGIN
                ALTER TABLE marketplace_templates DROP COLUMN IF EXISTS is_active;
            EXCEPTION
                WHEN others THEN null;
            END;
        END $$;
    """)
    
    # Revert category column to varchar
    op.execute("""
        DO $$ BEGIN
            IF (SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'marketplace_templates' AND column_name = 'category') = 'USER-DEFINED' THEN
                ALTER TABLE marketplace_templates 
                ALTER COLUMN category TYPE VARCHAR 
                USING category::VARCHAR;
            END IF;
        END $$;
    """)
    
    # Drop enum if no other table uses it
    op.execute("DROP TYPE IF EXISTS templatecategory CASCADE")
