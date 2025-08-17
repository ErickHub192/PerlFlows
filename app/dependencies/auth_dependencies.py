# app/dependencies/auth_dependencies.py

from fastapi import Depends
from app.services.auth_resolver import CentralAuthResolver, get_auth_resolver
from app.services.oauth_service import OAuthService, get_oauth_service
from app.services.auth_policy_service import AuthPolicyService, get_auth_policy_service

async def get_central_auth_resolver(
    auth_policy_service: AuthPolicyService = Depends(get_auth_policy_service)
) -> CentralAuthResolver:
    """Factory for CentralAuthResolver with FastAPI DI"""
    return CentralAuthResolver(auth_policy_service)