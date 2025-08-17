#!/usr/bin/env python3
"""
Seed script para popular marketplace templates con templates predefinidos
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import get_db
from app.db.models import MarketplaceTemplate, TemplateCategory
from sqlalchemy import select, func


def load_template_json(template_file: str) -> dict:
    """Load template JSON from templates/seeds directory"""
    template_path = project_root / "templates" / "seeds" / template_file
    with open(template_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def seed_templates():
    """Seed marketplace with initial templates"""
    
    # Template definitions
    templates_to_seed = [
        {
            "file": "mexican_business_assistant.json",
            "category": TemplateCategory.MEXICO_LATAM
        },
        {
            "file": "ai_sales_rep.json", 
            "category": TemplateCategory.BUSINESS_SALES
        },
        {
            "file": "customer_support_ai.json",
            "category": TemplateCategory.CUSTOMER_SERVICE
        }
    ]
    
    # Get database session
    async for db in get_db():
        try:
            # Check if templates already exist
            result = await db.execute(select(func.count(MarketplaceTemplate.template_id)))
            existing_count = result.scalar()
            if existing_count > 0:
                print(f"Templates already exist ({existing_count} found). Skipping seed.")
                return
            
            print("Seeding marketplace templates...")
            
            for template_def in templates_to_seed:
                try:
                    # Load template JSON
                    template_data = load_template_json(template_def["file"])
                    
                    # Create database record with all columns
                    template = MarketplaceTemplate(
                        name=template_data["name"],
                        category=template_def["category"],
                        description=template_data["description"],
                        spec_json=template_data,
                        tags=template_data.get("tags", []),
                        price_usd=template_data.get("price_usd", 0),
                        usage_count=0,
                        is_active=True
                    )
                    
                    db.add(template)
                    print(f"  Added: {template_data['name']} (${template_data.get('price_usd', 0)/100:.2f})")
                    
                except Exception as e:
                    print(f"  Error loading {template_def['file']}: {e}")
                    continue
            
            # Commit all templates
            await db.commit()
            
            # Final count
            result = await db.execute(select(func.count(MarketplaceTemplate.template_id)))
            final_count = result.scalar()
            print(f"\nSuccessfully seeded {final_count} templates!")
            
            # List seeded templates
            result = await db.execute(select(MarketplaceTemplate))
            templates = result.scalars().all()
            print("\nSeeded Templates:")
            for t in templates:
                print(f"  • {t.name} ({t.category.value}) - ${t.price_usd/100:.2f}")
            
        except Exception as e:
            print(f"Error seeding templates: {e}")
            await db.rollback()
            raise
        
        break  # Exit async generator


if __name__ == "__main__":
    print("Starting marketplace templates seed...")
    asyncio.run(seed_templates())
    print("Seed completed!")