"""
Discover User Files Handler - Tool para Kyra
Permite que Kyra descubra archivos reales del usuario en providers conectados
"""
import logging
from typing import Dict, Any, List
import json

from app.services.file_discovery_service import FileDiscoveryService, get_file_discovery_service
from app.services.credential_service import CredentialService, get_credential_service
from app.services.auth_resolver import CentralAuthResolver, get_auth_resolver
from app.connectors.factory import register_tool
from app.handlers.connector_handler import ActionHandler

logger = logging.getLogger(__name__)


@register_tool("discover_user_files")
class DiscoverUserFilesHandler(ActionHandler):
    """
    ✅ CORREGIDO: Tool handler con dependency injection apropiada
    Permite que Kyra descubra archivos reales del usuario usando servicios centralizados
    """
    
    def __init__(self, credentials: dict = None):
        super().__init__()
        self.credentials = credentials
        # Las dependencias se resuelven en execute(), no en __init__
    
    async def execute(self, params: Dict[str, Any], credentials: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Descubre archivos reales del usuario en providers conectados
        
        Args:
            params: Parámetros con user_id, selected_nodes, file_types
            credentials: Credenciales del usuario (obtenidas automáticamente)
        
        Returns:
            Dict con archivos descubiertos y metadata
        """
        try:
            user_id = params.get("user_id")
            selected_nodes = params.get("selected_nodes", [])
            file_types = params.get("file_types")
            
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required",
                    "discovered_files": []
                }
            
            if not selected_nodes:
                return {
                    "success": False, 
                    "error": "selected_nodes is required",
                    "discovered_files": []
                }
            
            logger.info(f"Kyra discovering files for user {user_id} with {len(selected_nodes)} nodes")
            
            # ✅ CORREGIDO: Crear instancias manualmente ya que no estamos en FastAPI context
            from app.services.credential_service import get_credential_service
            from app.services.auth_resolver import CentralAuthResolver
            from app.services.auth_policy_service import AuthPolicyService
            from app.repositories.auth_policy_repository import AuthPolicyRepository
            from app.db.database import get_db
            
            # Crear DB session manualmente
            db_generator = get_db()
            db = await db_generator.__anext__()
            
            try:
                # Crear auth_policy_service manualmente
                auth_policy_repo = AuthPolicyRepository(db)
                auth_policy_service = AuthPolicyService(db, auth_policy_repo)
                
                # Crear credential_service manualmente
                from app.repositories.credential_repository import CredentialRepository
                credential_repo = CredentialRepository(db)
                credential_service = CredentialService(credential_repo)
                
                # Crear auth_resolver
                auth_resolver = CentralAuthResolver(auth_policy_service)
                
                # Crear discovery_service
                discovery_service = FileDiscoveryService(
                    credential_service=credential_service,
                    auth_resolver=auth_resolver
                )
                
            finally:
                # La sesión se cerrará automáticamente al final del scope
                await db.close()
            
            # Convertir selected_nodes a formato esperado por discovery service
            planned_steps = [
                {
                    "id": node.get("node_id", f"step_{i}"),
                    "default_auth": node.get("default_auth"),
                    "action_id": node.get("action_id")
                }
                for i, node in enumerate(selected_nodes)
                if node.get("default_auth") or node.get("action_id")
            ]
            
            # ✅ CORREGIDO: Usar discovery service con DI apropiada
            discovered_files_objects = await discovery_service.discover_user_files(
                user_id=user_id,
                planned_steps=planned_steps,
                file_types=file_types
            )
            
            # Convertir objetos a dict para serialización
            discovered_files = []
            for file_obj in discovered_files_objects:
                discovered_files.append({
                    "id": file_obj.id,
                    "name": file_obj.name,
                    "provider": file_obj.provider,
                    "file_type": file_obj.file_type,
                    "confidence": file_obj.confidence,
                    "structure": file_obj.structure,
                    "icon": file_obj.icon,
                    "metadata": file_obj.metadata
                })
            
            result = {
                "success": True,
                "discovered_files": discovered_files,
                "total_files": len(discovered_files),
                "providers_used": len(planned_steps),
                "file_types_found": list(set(f.get("file_type", "unknown") for f in discovered_files))
            }
            
            logger.info(f"Kyra discovered {len(discovered_files)} files from {len(planned_steps)} steps")
            return result
            
        except Exception as e:
            logger.error(f"Error in discover_user_files_handler: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Discovery failed: {str(e)}",
                "discovered_files": []
            }

