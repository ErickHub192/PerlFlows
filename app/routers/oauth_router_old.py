"""
OAuth Router refactorizado para usar el nuevo sistema agnóstico
Reemplaza oauth_router.py con funcionalidad agnóstica y escalable
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.oauth_service import OAuthService
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service
from app.db.database import get_db

router = APIRouter(prefix="/api/oauth", tags=["oauth"])
security = HTTPBearer()


@router.get("/initiate")
async def oauth_initiate_agnostic(
    service_id: str = Query(..., description="Service ID (ej: 'gmail', 'slack')"),
    chat_id: str = Query(..., description="Chat ID"),
    token: Optional[str] = Query(None, description="JWT token for browser redirects"),
    user_id: Optional[int] = None,
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
                        detail=f"Invalid token: {str(e)}"
                    )
            else:
                # For API calls with headers, dependency injection handles this
                # This branch should not be reached since user_id dependency will fail first
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required: provide valid JWT token as query parameter"
                )
        
        # Get auth policy for this service_id
        auth_policy = await auth_policy_service.get_auth_policy_by_service_id(service_id)
        
        if not auth_policy:
            raise HTTPException(
                status_code=404,
                detail=f"No auth policy found for service_id: {service_id}"
            )
        
        if auth_policy["mechanism"] != "oauth2":
            raise HTTPException(
                status_code=400,
                detail=f"Service {service_id} does not use OAuth2 mechanism"
            )
        
        # Get authenticator class dynamically
        provider = auth_policy["provider"]
        authenticator_class = get_registered_class("oauth2", provider)
        
        if not authenticator_class:
            raise HTTPException(
                status_code=400,
                detail=f"No OAuth authenticator found for provider: {provider}"
            )
        
        # Create authenticator instance and get authorization URL
        from app.db.database import get_db
        async for db in get_db():
            authenticator = authenticator_class(
                user_id=user_id, 
                db=db, 
                auth_policy=auth_policy
            )
            auth_url = await authenticator.authorization_url()
            await db.commit()  # ✅ Commit the OAuth state save
            break
        
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
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    Procesa OAuth callback agnóstico
    ✅ AGNÓSTICO - maneja cualquier provider automáticamente
    """
    try:
        # Get user_id and service_id from OAuth state (since Google callback doesn't have JWT)
        from app.repositories.oauth_state_repository import OAuthStateRepository
        from app.db.database import get_db
        
        user_id = None
        provider = None
        extracted_service_id = None
        extracted_chat_id = None
        
        async for db in get_db():
            if state:
                state_repo = OAuthStateRepository(db)
                oauth_data = await state_repo.get_oauth_state_by_state(state)
                print(f"🔍 OAuth callback debug - state: {state}, oauth_data: {oauth_data}")
                if oauth_data:
                    if len(oauth_data) >= 4:
                        user_id, provider, extracted_service_id, extracted_chat_id = oauth_data[:4]
                        print(f"✅ OAuth data found - user_id: {user_id}, provider: {provider}, service_id: {extracted_service_id}, chat_id: {extracted_chat_id}")
                    else:
                        # Fallback for old records without chat_id
                        user_id, provider, extracted_service_id = oauth_data[:3]
                        print(f"✅ OAuth data found (legacy) - user_id: {user_id}, provider: {provider}, service_id: {extracted_service_id}")
                    # Clean up the used state
                    await state_repo.delete_oauth_state_by_state(state)
                    await db.commit()
                else:
                    print(f"❌ No OAuth data found for state: {state}")
            break
            
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state"
            )
            
        # Use extracted service_id from state if not provided in query
        if not service_id:
            service_id = extracted_service_id
        
        # Get auth policy for this service_id
        auth_policy = await auth_policy_service.get_auth_policy_by_service_id(service_id)
        
        if not auth_policy:
            raise HTTPException(
                status_code=404,
                detail=f"No auth policy found for service_id: {service_id}"
            )
        
        # Get authenticator class dynamically
        provider = auth_policy["provider"]
        authenticator_class = get_registered_class("oauth2", provider)
        
        if not authenticator_class:
            raise HTTPException(
                status_code=400,
                detail=f"No OAuth authenticator found for provider: {provider}"
            )
        
        # Process token exchange
        async for db in get_db():
            authenticator = authenticator_class(
                user_id=user_id, 
                db=db, 
                auth_policy=auth_policy,
                chat_id=extracted_chat_id
            )
            # Pass None as state since we already validated it
            await authenticator.fetch_token(code, None)
            break
        
        # Return HTML page for popup closure
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Success</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
                <h2>✅ Autorización exitosa</h2>
                <p>Cerrando ventana...</p>
            </div>
            <script>
                // Send success message to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'OAUTH_SUCCESS',
                        code: '{code}',
                        state: '{state or ''}',
                        service: '{service_id}'
                    }}, 'http://localhost:5173');
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 1000);
                }} else {{
                    // If not popup, redirect to main app
                    window.location.href = '/';
                }}
            </script>
        </body>
        </html>
        """)
        
    except HTTPException as he:
        # Return error HTML page for popup
        error_msg = he.detail if hasattr(he, 'detail') else str(he)
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Error</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
                <h2>❌ Error en autorización</h2>
                <p>{error_msg}</p>
                <p>Cerrando ventana...</p>
            </div>
            <script>
                // Send error message to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'OAUTH_ERROR',
                        error: '{error_msg}',
                        service: '{service_id or 'unknown'}'
                    }}, 'http://localhost:5173');
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                }} else {{
                    // If not popup, redirect to main app
                    setTimeout(() => {{
                        window.location.href = '/';
                    }}, 3000);
                }}
            </script>
        </body>
        </html>
        """)
    except Exception as e:
        # Return error HTML page for popup
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Error</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
                <h2>❌ Error del servidor</h2>
                <p>{str(e)}</p>
                <p>Cerrando ventana...</p>
            </div>
            <script>
                // Send error message to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'OAUTH_ERROR',
                        error: '{str(e)}',
                        service: '{service_id or 'unknown'}'
                    }}, 'http://localhost:5173');
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                }} else {{
                    // If not popup, redirect to main app
                    setTimeout(() => {{
                        window.location.href = '/';
                    }}, 3000);
                }}
            </script>
        </body>
        </html>
        """)


@router.post("/workflow/check-requirements", response_model=WorkflowAuthAnalysisDTO)
async def check_workflow_oauth_requirements_new(
    flow_spec: dict = Body(...),
    chat_id: str = Body(...),
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    ✅ NUEVA API AGNÓSTICA: Verifica auth requirements para workflow
    Reemplaza el endpoint legacy con funcionalidad agnóstica
    
    Args:
        flow_spec: Especificación completa del workflow
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        WorkflowAuthAnalysisDTO con análisis completo
    """
    try:
        # user_id is already provided by dependency
        
        analysis = await auto_auth_trigger.analyze_workflow_auth_requirements(
            flow_spec=flow_spec,
            user_id=user_id,
            chat_id=chat_id
        )
        
        return analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking workflow OAuth requirements: {str(e)}"
        )


@router.post("/steps/check-requirements")
async def check_steps_oauth_requirements_legacy(
    planned_steps: List[Dict[str, Any]] = Body(...),
    chat_id: str = Body(..., description="Chat ID"),
    user_id: int = Depends(get_current_user_id),
    auto_auth_trigger: AutoAuthTrigger = Depends(get_auto_auth_trigger)
):
    """
    ✅ ENDPOINT DE COMPATIBILIDAD: Para frontend legacy
    Convierte formato legacy a nuevo formato agnóstico
    
    Args:
        planned_steps: Lista de pasos en formato legacy
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        Formato legacy compatible con frontend existente
    """
    try:
        # user_id is already provided by dependency
        
        # Convert legacy format to new flow_spec format
        flow_spec = {
            "nodes": []
        }
        
        for step in planned_steps:
            if step.get("default_auth"):
                flow_spec["nodes"].append({
                    "id": step.get("step_id", step.get("id")),
                    "actions": [{
                        "id": step.get("action_id"),
                        "name": step.get("action_name", "unknown")
                    }]
                })
        
        # Use new agnostic analysis
        analysis = await auto_auth_trigger.analyze_workflow_auth_requirements(
            flow_spec=flow_spec,
            user_id=user_id,
            chat_id=chat_id
        )
        
        # Convert back to legacy format for frontend compatibility
        missing_oauth = []
        for req in analysis.missing_requirements:
            missing_oauth.append({
                "service": req.service_id,
                "provider": req.provider,
                "flavor": req.service,
                "oauth_url": f"/api/oauth/initiate?service_id={req.service_id}&chat_id={chat_id}",
                "authorization_url": f"/api/oauth/initiate?service_id={req.service_id}&chat_id={chat_id}",
                "display_name": req.display_name,
                "scopes": req.required_scopes,
                "mechanism": req.mechanism
            })
        
        return {
            "missing_oauth": missing_oauth,
            "ready_to_execute": analysis.can_execute,
            "total_services_needed": analysis.total_requirements,
            "authenticated_count": analysis.satisfied_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking steps OAuth requirements: {str(e)}"
        )


@router.get("/services/available")
async def get_available_oauth_services(
    user_id: int = Depends(get_current_user_id),
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
):
    """
    ✅ NUEVA API: Lista servicios OAuth disponibles
    ✅ AGNÓSTICO - lista dinámicamente desde BD
    
    Returns:
        Lista de servicios OAuth disponibles
    """
    try:
        policies = await auth_policy_service.get_all_active_policies()
        
        oauth_services = []
        for policy in policies:
            if policy.get("mechanism") == "oauth2":
                oauth_services.append({
                    "service_id": policy.get("auth_string", "").replace("oauth2_", ""),
                    "provider": policy.get("provider"),
                    "service": policy.get("service"),
                    "display_name": policy.get("display_name"),
                    "description": policy.get("description"),
                    "max_scopes": policy.get("max_scopes", []),
                    "is_active": policy.get("is_active", True)
                })
        
        return {
            "oauth_services": oauth_services,
            "total_count": len(oauth_services)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting available OAuth services: {str(e)}"
        )


@router.get("/service/{service_id}/status")
async def get_oauth_service_status(
    service_id: str,
    chat_id: str = Query(...),
    user_id: int = Depends(get_current_user_id),
    credential_service: CredentialService = Depends(get_credential_service)
):
    """
    ✅ NUEVA API: Verifica status de OAuth para un servicio
    ✅ AGNÓSTICO - funciona con cualquier service_id
    
    Args:
        service_id: ID del servicio
        chat_id: ID del chat
        current_user: Usuario autenticado
        
    Returns:
        Status de autenticación del servicio
    """
    try:
        # user_id is already provided by dependency
        
        # Check if user has credentials for this service
        credentials = await credential_service.get_credential(user_id, service_id, chat_id)
        
        return {
            "service_id": service_id,
            "is_authenticated": credentials is not None,
            "expires_at": credentials.get("expires_at") if credentials else None,
            "scopes": credentials.get("scopes") if credentials else [],
            "last_updated": credentials.get("updated_at") if credentials else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting OAuth service status: {str(e)}"
        )