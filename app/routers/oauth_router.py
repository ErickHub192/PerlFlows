"""
OAuth Router refactorizado - Solo orquestación, lógica de negocio en service
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.oauth_service import OAuthService
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service
from app.services.chat_service_clean import ChatService, get_chat_service
from app.db.database import get_db
from app.core.auth import get_current_user_id
from app.dtos.oauth_app_dto import OAuthAppCreateRequest, OAuthAppResponse, OAuthAppsListResponse, OAuthAppUpdateRequest
from uuid import UUID

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

# 🆕 NUEVO: Router para oauth-apps (compatibilidad con frontend)
oauth_apps_router = APIRouter(prefix="/api/oauth-apps", tags=["oauth-apps"])


@router.get("/check-credentials/{service_id}")
async def check_oauth_credentials(
    service_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Verifica si el usuario tiene credenciales OAuth configuradas antes del flow
    Retorna JSON indicando si necesita configuración
    """
    try:
        from app.repositories.credential_repository import CredentialRepository
        cred_repo = CredentialRepository(db)
        
        # Get auth policy to extract provider info
        auth_policy = await auth_policy_service.get_auth_policy_by_service_id(service_id)
        if not auth_policy:
            raise HTTPException(status_code=404, detail=f"No auth policy found for service_id: {service_id}")
        
        provider = auth_policy["provider"]
        
        # Check if user has client_id/client_secret configured
        existing_cred = await cred_repo.get_credential(user_id, service_id, chat_id=None)
        has_user_credentials = (
            existing_cred and 
            existing_cred.get("client_id") and 
            existing_cred.get("client_secret") and
            existing_cred.get("config", {}).get("user_configured", False)
        )
        
        # Check if user has OAuth access_token (already authorized)
        has_oauth_token = existing_cred and existing_cred.get("access_token") is not None
        
        return {
            "service_id": service_id,
            "provider": provider,
            "display_name": auth_policy.get("display_name", f"{provider.title()}"),
            "needs_configuration": not has_user_credentials,
            "has_oauth_token": has_oauth_token,
            "can_use_system_credentials": True,  # Always allow system fallback
            "existing_app_name": existing_cred.get("config", {}).get("app_name") if existing_cred else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking OAuth credentials: {str(e)}"
        )


@router.get("/initiate")
async def oauth_initiate_agnostic(
    service_id: str = Query(..., description="Service ID (ej: 'gmail', 'slack')"),
    chat_id: str = Query(..., description="Chat ID"),
    token: Optional[str] = Query(None, description="JWT token for browser redirects"),
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Inicia OAuth flow agnóstico usando service_id
    ✅ AGNÓSTICO - obtiene mechanism dinámicamente de la BD
    """
    try:
        # Handle authentication - either from dependency or token parameter
        if user_id is None:
            if token:
                # Manual JWT validation for browser redirects
                try:
                    from app.core.auth import verify_jwt_token
                    user_id = verify_jwt_token(token)
                except Exception as e:
                    raise HTTPException(
                        status_code=401,
                        detail=f"Invalid JWT token: {str(e)}"
                    )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required: provide valid JWT token as query parameter"
                )
        
        # Delegate business logic to service
        oauth_service = OAuthService(db, auth_policy_service)
        auth_url = await oauth_service.initiate_oauth_flow(service_id, chat_id, user_id)
        
        return RedirectResponse(url=auth_url)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error initiating OAuth: {str(e)}"
        )


@router.get("/callback")
async def oauth_callback_agnostic(
    code: str = Query(..., description="Authorization code"),
    state: Optional[str] = Query(None, description="CSRF state"),
    service_id: Optional[str] = Query(None, description="Service ID (optional, extracted from state if not provided)"),
    db: AsyncSession = Depends(get_db),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Callback agnóstico para OAuth2 - maneja cualquier proveedor
    ✅ AGNÓSTICO - extrae user_id y service_id del state guardado
    """
    try:
        if not state:
            raise HTTPException(
                status_code=400,
                detail="Missing required 'state' parameter"
            )
        
        # Delegate business logic to service
        oauth_service = OAuthService(db, auth_policy_service)
        result = await oauth_service.handle_oauth_callback(code, state, service_id)
        
        # Return HTML page for popup closure
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Success</title>
        </head>
        <body>
            <script>
                try {{
                    window.opener.postMessage({{
                        type: 'OAUTH_SUCCESS',
                        user_id: {result['user_id']},
                        service_id: '{result['service_id']}',
                        provider: '{result['provider']}'
                    }}, 'http://localhost:5173');
                    window.close();
                }} catch (error) {{
                    console.error('Error posting message:', error);
                    document.body.innerHTML = '<h1>OAuth Successful!</h1><p>You can close this window.</p>';
                }}
            </script>
            <h1>OAuth Successful!</h1>
            <p>Cerrando ventana...</p>
        </body>
        </html>
        """)
        
    except HTTPException:
        raise
    except Exception as e:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Error</title>
        </head>
        <body>
            <h1>Error en autorización</h1>
            <p>Error creando credencial: {str(e)}</p>
            <script>
                try {{
                    window.opener.postMessage({{
                        type: 'OAUTH_ERROR',
                        error: '{str(e)}'
                    }}, 'http://localhost:5173');
                    window.close();
                }} catch (error) {{
                    console.error('Error posting message:', error);
                }}
            </script>
        </body>
        </html>
        """, status_code=500)


# 🆕 ENDPOINTS OAUTH-APPS (compatibilidad con frontend)

@oauth_apps_router.get("/", response_model=OAuthAppsListResponse)
async def get_user_oauth_apps(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    GET /api/oauth-apps/ - Obtener todas las OAuth apps del usuario
    """
    try:
        from app.repositories.credential_repository import CredentialRepository
        cred_repo = CredentialRepository(db)
        
        # Obtener todas las credenciales OAuth del usuario
        credentials = await cred_repo.list_user_oauth_credentials(user_id)
        
        oauth_apps = []
        for cred in credentials:
            oauth_apps.append(OAuthAppResponse(
                provider=cred["service_id"],
                client_id=cred["client_id"],
                app_name=cred.get("app_name", f"{cred['service_id'].title()} App"),
                created_at=cred.get("created_at", "").isoformat() if cred.get("created_at") else "2025-01-01T00:00:00Z",
                is_active=True
            ))
        
        return OAuthAppsListResponse(oauth_apps=oauth_apps, total=len(oauth_apps))
        
    except Exception as e:
        import traceback
        error_detail = f"Error fetching OAuth apps: {str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@oauth_apps_router.post("/{provider}", response_model=OAuthAppResponse)
async def create_oauth_app(
    provider: str,
    oauth_app: OAuthAppCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    POST /api/oauth-apps/{provider} - Crear nueva OAuth app
    Reutiliza la lógica existente de credenciales
    """
    try:
        from app.repositories.credential_repository import CredentialRepository
        cred_repo = CredentialRepository(db)
        
        # Guardar usando el método correcto del repository
        result = await cred_repo.save_oauth_credentials(
            user_id=user_id,
            provider=provider,
            client_id=oauth_app.client_id,
            client_secret=oauth_app.client_secret,
            app_name=oauth_app.app_name
        )
        
        return OAuthAppResponse(
            provider=provider,
            client_id=oauth_app.client_id,
            app_name=oauth_app.app_name,
            created_at=result.get("created_at", "").isoformat() if result.get("created_at") else "2025-01-01T00:00:00Z",
            is_active=True
        )
        
    except Exception as e:
        import traceback
        error_detail = f"Error creating OAuth app: {str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@oauth_apps_router.get("/{provider}", response_model=OAuthAppResponse)
async def get_oauth_app(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    GET /api/oauth-apps/{provider} - Obtener OAuth app específica
    """
    try:
        from app.repositories.credential_repository import CredentialRepository
        cred_repo = CredentialRepository(db)
        
        credential = await cred_repo.get_credential(user_id, provider, chat_id=None)
        
        if not credential or not credential.get("client_id"):
            raise HTTPException(status_code=404, detail=f"OAuth app for {provider} not found")
        
        return OAuthAppResponse(
            provider=provider,
            client_id=credential["client_id"],
            app_name=credential.get("config", {}).get("app_name", f"{provider.title()} App"),
            created_at=credential.get("created_at", ""),
            is_active=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching OAuth app: {str(e)}")


@oauth_apps_router.put("/{provider}", response_model=OAuthAppResponse)
async def update_oauth_app(
    provider: str,
    oauth_app: OAuthAppUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    PUT /api/oauth-apps/{provider} - Actualizar OAuth app
    """
    try:
        from app.repositories.credential_repository import CredentialRepository
        cred_repo = CredentialRepository(db)
        
        # Obtener credencial existente
        existing_cred = await cred_repo.get_credential(user_id, provider, chat_id=None)
        if not existing_cred:
            raise HTTPException(status_code=404, detail=f"OAuth app for {provider} not found")
        
        # Actualizar solo campos proporcionados
        updated_data = existing_cred.copy()
        if oauth_app.client_id is not None:
            updated_data["client_id"] = oauth_app.client_id
        if oauth_app.client_secret is not None:
            updated_data["client_secret"] = oauth_app.client_secret
        if oauth_app.app_name is not None:
            updated_data.setdefault("config", {})["app_name"] = oauth_app.app_name
        
        # Guardar actualización
        await cred_repo.save_credential(
            user_id=user_id,
            service_id=provider,
            credential_data=updated_data,
            chat_id=None
        )
        
        return OAuthAppResponse(
            provider=provider,
            client_id=updated_data["client_id"],
            app_name=updated_data.get("config", {}).get("app_name", f"{provider.title()} App"),
            created_at=updated_data.get("created_at", ""),
            is_active=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating OAuth app: {str(e)}")


@oauth_apps_router.delete("/{provider}")
async def delete_oauth_app(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    DELETE /api/oauth-apps/{provider} - Eliminar OAuth app
    """
    try:
        from app.repositories.credential_repository import CredentialRepository
        cred_repo = CredentialRepository(db)
        
        # Verificar que existe
        existing_cred = await cred_repo.get_credential(user_id, provider, chat_id=None)
        if not existing_cred:
            raise HTTPException(status_code=404, detail=f"OAuth app for {provider} not found")
        
        # Eliminar credencial
        await cred_repo.delete_credential(user_id, provider, chat_id=None)
        
        return {"message": f"OAuth app for {provider} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting OAuth app: {str(e)}")


