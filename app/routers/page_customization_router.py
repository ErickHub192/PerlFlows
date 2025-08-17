from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List
from app.dtos.page_customization_dto import (
    PageCustomizationRequestDto,
    PageCustomizationResponseDto,
    PageTemplateDto
)
from app.services.page_customization_service import PageCustomizationService
from app.core.auth import get_current_user_id
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/page-customization", tags=["Page Customization"])

# Dependency injection
from app.services.page_customization_service import get_page_customization_service


@router.post("/agents/{agent_id}/customize", response_model=PageCustomizationResponseDto)
async def customize_page(
    agent_id: str,
    request: PageCustomizationRequestDto,
    service: PageCustomizationService = Depends(get_page_customization_service),
    # current_user = Depends(get_current_user)  # Uncomment when auth is needed
):
    """
    Personaliza una página web usando lenguaje natural
    
    - **agent_id**: ID del agente cuya página se va a personalizar
    - **customization_prompt**: Descripción en lenguaje natural de los cambios deseados
    - **target_element**: Elemento específico a modificar (opcional)
    
    Ejemplos de prompts:
    - "Cambia el color de fondo a azul claro"
    - "Agrega un logo en la esquina superior izquierda"
    - "Cambia la fuente del texto a una más moderna"
    - "Haz que los botones sean más grandes y redondos"
    """
    try:
        # Ensure agent_id matches between URL and request body
        request.agent_id = agent_id
        
        logger.info(f"Customizing page for agent {agent_id} with prompt: {request.customization_prompt}")
        
        result = await service.customize_page(request)
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Customization failed: {result.error_message}"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in customize_page endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/agents/{agent_id}/template", response_model=PageTemplateDto)
async def get_current_template(
    agent_id: str,
    service: PageCustomizationService = Depends(get_page_customization_service),
    # current_user = Depends(get_current_user)  # Uncomment when auth is needed
):
    """
    Obtiene el template actual de una página web
    
    - **agent_id**: ID del agente
    
    Returns:
        Template actual con HTML, CSS y metadata
    """
    try:
        template = await service.get_current_template(agent_id)
        return template
        
    except Exception as e:
        logger.error(f"Error getting template for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving template: {str(e)}"
        )


@router.post("/agents/{agent_id}/preview")
async def preview_changes(
    agent_id: str,
    changes: Dict[str, Any],
    service: PageCustomizationService = Depends(get_page_customization_service),
    # current_user = Depends(get_current_user)  # Uncomment when auth is needed
):
    """
    Genera un preview de cambios sin aplicarlos permanentemente
    
    - **agent_id**: ID del agente
    - **changes**: Diccionario con los cambios a previsualizar
    
    Returns:
        HTML con los cambios aplicados temporalmente
    """
    try:
        preview_html = await service.preview_changes(agent_id, changes)
        
        if not preview_html:
            raise HTTPException(
                status_code=400,
                detail="Could not generate preview"
            )
        
        return HTMLResponse(content=preview_html)
        
    except Exception as e:
        logger.error(f"Error generating preview for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating preview: {str(e)}"
        )


@router.get("/agents/{agent_id}/template/history", response_model=List[PageTemplateDto])
async def get_template_history(
    agent_id: str,
    limit: int = Query(10, ge=1, le=50, description="Número máximo de templates a retornar"),
    service: PageCustomizationService = Depends(get_page_customization_service),
    # current_user = Depends(get_current_user)  # Uncomment when auth is needed
):
    """
    Obtiene el historial de templates de un agente
    
    - **agent_id**: ID del agente
    - **limit**: Número máximo de templates a retornar (default: 10, max: 50)
    
    Returns:
        Lista de templates históricos ordenados por fecha
    """
    try:
        templates = await service.get_template_history(agent_id)
        return templates[:limit]
        
    except Exception as e:
        logger.error(f"Error getting template history for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving template history: {str(e)}"
        )


@router.post("/agents/{agent_id}/template/rollback/{template_id}")
async def rollback_template(
    agent_id: str,
    template_id: str,
    service: PageCustomizationService = Depends(get_page_customization_service),
    # current_user = Depends(get_current_user)  # Uncomment when auth is needed
):
    """
    Revierte a una versión anterior del template
    
    - **agent_id**: ID del agente
    - **template_id**: ID del template al que revertir
    
    Returns:
        Confirmación de que el rollback fue exitoso
    """
    try:
        success = await service.rollback_template(agent_id, template_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Rollback failed"
            )
        
        return {
            "success": True,
            "message": f"Successfully rolled back to template {template_id}",
            "agent_id": agent_id,
            "template_id": template_id
        }
        
    except Exception as e:
        logger.error(f"Error rolling back template for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during rollback: {str(e)}"
        )


@router.get("/agents/{agent_id}/render", response_class=HTMLResponse)
async def render_customized_page(
    agent_id: str,
    preview: bool = Query(False, description="Si es true, muestra preview sin guardar cambios"),
    service: PageCustomizationService = Depends(get_page_customization_service)
):
    """
    Renderiza la página personalizada de un agente
    
    - **agent_id**: ID del agente
    - **preview**: Si es true, renderiza en modo preview
    
    Returns:
        HTML completo de la página personalizada
    """
    try:
        template = await service.get_current_template(agent_id)
        
        # Add preview indicator if needed
        html_content = template.html_content
        if preview:
            preview_banner = """
            <div style="position: fixed; top: 0; left: 0; right: 0; background: #fbbf24; color: #92400e; text-align: center; padding: 8px; z-index: 9999; font-weight: bold;">
                🔍 MODO PREVIEW - Los cambios no han sido guardados
            </div>
            <style>
                body { margin-top: 40px !important; }
            </style>
            """
            html_content = html_content.replace("<body", f"{preview_banner}<body")
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error rendering page for agent {agent_id}: {str(e)}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Could not render page: {str(e)}</p></body></html>",
            status_code=500
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for the page customization service"""
    return {
        "status": "healthy",
        "service": "page-customization",
        "version": "1.0.0"
    }