from datetime import datetime
from uuid import UUID
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class MarketplaceTemplateDTO(BaseModel):
    template_id: UUID
    name: str
    category: str
    description: Optional[str] = None
    spec_json: Dict[str, Any]
    tags: Optional[List[str]] = None
    price_usd: int = Field(description="Price in USD cents")
    usage_count: int = Field(description="Number of times template has been installed")
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    # Computed fields from spec_json
    tools: Optional[List[str]] = Field(None, description="Tools used by this template")
    deployment_channels: Optional[List[str]] = Field(None, description="Supported deployment channels")
    use_cases: Optional[List[str]] = Field(None, description="Template use cases")
    target_audience: Optional[str] = Field(None, description="Target audience")
    
    @classmethod
    def from_orm(cls, template):
        """Create DTO from database model with computed fields"""
        data = {
            "template_id": template.template_id,
            "name": template.name,
            "category": template.category.value if hasattr(template.category, 'value') else template.category,
            "description": template.description,
            "spec_json": template.spec_json,
            "tags": template.tags,
            "price_usd": template.price_usd,
            "usage_count": template.usage_count,
            "is_active": template.is_active,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
        
        # Extract additional fields from spec_json
        if isinstance(template.spec_json, dict):
            data.update({
                "tools": template.spec_json.get("tools"),
                "deployment_channels": template.spec_json.get("deployment_channels"),
                "use_cases": template.spec_json.get("use_cases"),
                "target_audience": template.spec_json.get("target_audience"),
            })
        
        return cls(**data)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Asistente de Negocio Mexicano",
                "category": "mexico_latam",
                "description": "Automatiza contabilidad SAT, facturas y compliance fiscal",
                "tags": ["sat", "mexico", "contabilidad"],
                "price_usd": 7900,
                "usage_count": 25,
                "is_active": True,
                "tools": ["sat_descarga_cfdi", "gmail_send_message", "sheets_read_write"],
                "deployment_channels": ["telegram", "web_embed"],
                "use_cases": ["Automatización de facturas SAT", "Reportes fiscales"],
                "target_audience": "PYMES mexicanas"
            }
        }
