"""
🔥 REFACTORED: File Discovery Service - SOLO descubre archivos/metadata de nodos
SEPARACIÓN LIMPIA: No maneja auth, recibe credenciales ya verificadas
RESPONSABILIDAD ÚNICA: Discovery de archivos/metadata de providers
NO confundir con Auth Service Discovery
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# ✅ SEPARACIÓN LIMPIA: Solo necesita CredentialService para credenciales
from app.services.credential_service import CredentialService, get_credential_service
from app.services.auth_resolver import CentralAuthResolver, get_auth_resolver
from app.dtos.file_discovery_dto import DiscoveredFileDTO, FileDiscoveryResponseDTO
from fastapi import Depends

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredFile:
    """Archivo descubierto dinámicamente"""
    id: str
    name: str
    provider: str
    file_type: str
    confidence: float = 0.8
    structure: Dict[str, Any] = None
    icon: str = "📄"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.structure is None:
            self.structure = {}
        if self.metadata is None:
            self.metadata = {}


class FileDiscoveryService:
    """
    🔥 REFACTORED: SOLO descubre archivos/metadata
    RESPONSABILIDAD ÚNICA:
    - Recibe credenciales ya verificadas de UnifiedOAuthManager
    - Usa discovery handlers para obtener archivos reales
    - NO maneja auth, NO extrae providers, NO verifica credenciales
    """
    
    def __init__(
        self, 
        credential_service: Optional[CredentialService] = None,
        auth_resolver: Optional[CentralAuthResolver] = None
    ):
        self.credential_service = credential_service
        self.auth_resolver = auth_resolver
        self.logger = logging.getLogger(__name__)
    
    async def discover_user_files(
        self,
        user_id: int,
        planned_steps: List[Dict[str, Any]],
        file_types: Optional[List[str]] = None
    ) -> List[DiscoveredFile]:
        """
        🔥 SIMPLIFICADO: SOLO descubre archivos
        
        Args:
            user_id: ID del usuario
            planned_steps: Pasos del workflow (para obtener credenciales)
            file_types: Tipos de archivo a buscar (opcional)
            
        Returns:
            Lista de archivos descubiertos por provider
        """
        try:
            if not self.credential_service or not self.auth_resolver:
                self.logger.error("CredentialService or AuthResolver not available")
                return []
            
            # ✅ SAFETY CHECK: Handle None planned_steps
            if planned_steps is None:
                self.logger.warning("planned_steps is None, returning empty discovery results")
                return []
            
            # ✅ SEPARACIÓN LIMPIA: Obtener credenciales usando CredentialService
            discovered_files = []
            
            # Procesar cada paso para obtener credenciales específicas
            for step in planned_steps:
                default_auth = step.get('default_auth')
                if not default_auth:
                    continue
                    
                # Resolver auth policy para extraer provider info
                auth_policy = await self.auth_resolver.resolve_auth_once(default_auth)
                if not auth_policy or not auth_policy.requires_oauth():
                    continue
                    
                # Obtener credenciales usando CredentialService
                credentials = await self.credential_service.get_credential(
                    user_id=user_id,
                    service_id=auth_policy.service
                )
                
                if not credentials:
                    self.logger.debug(f"No credentials found for {auth_policy.provider}")
                    continue
                # Descubrir archivos usando credenciales del CredentialService
                provider_files = await self._discover_files_for_provider(
                    auth_policy.provider, auth_policy.service, credentials, file_types
                )
                
                discovered_files.extend(provider_files)
                self.logger.debug(f"Found {len(provider_files)} files from {auth_policy.provider}")
            
            self.logger.info(f"Total discovered files: {len(discovered_files)}")
            return discovered_files
            
        except Exception as e:
            self.logger.error(f"Error discovering user files: {e}", exc_info=True)
            return []
    
    # ❌ ELIMINADO: _extract_providers_from_nodes() 
    # 🔥 MOTIVO: Movido a UnifiedOAuthManager.extract_providers_from_steps()
    # Esta función duplicó lógica que ya existía en otros lugares
    
    async def _discover_files_for_provider(
        self,
        provider: str,
        service: Optional[str],
        credentials: Dict[str, Any],
        file_types: Optional[List[str]]
    ) -> List[DiscoveredFile]:
        """
        🔥 SIMPLIFICADO: Descubre archivos para un provider específico
        Recibe credenciales ya verificadas, SOLO se enfoca en discovery
        """
        try:
            # Importar discovery handler dinámicamente CON credenciales
            handler = await self._get_connector_for_provider(provider, service, credentials)
            if not handler:
                self.logger.debug(f"No discovery handler available for {provider}/{service}")
                return []
            
            # Usar handler para descubrir archivos (ya tiene credenciales)
            files = await handler.discover_files(file_types)
            
            # Convertir a DiscoveredFile
            discovered_files = []
            for file_data in files:
                discovered_file = self._create_discovered_file(file_data, provider)
                if discovered_file:
                    discovered_files.append(discovered_file)
            
            return discovered_files
            
        except Exception as e:
            self.logger.error(f"Error discovering files for {provider}: {e}")
            return []
    
    async def _get_connector_for_provider(
        self, 
        provider: str, 
        service: Optional[str],
        credentials: Dict[str, Any]
    ):
        """
        🔥 SIMPLIFICADO: Obtiene discovery handler usando factory
        Recibe credenciales ya verificadas
        """
        try:
            from app.handlers.discovery.discovery_factory import get_discovery_handler
            
            # Mapear provider + service a handler específico
            handler_name = self._get_handler_name(provider, service)
            
            # Pasar credenciales limpias al handler
            extended_credentials = {
                **credentials,
                "provider_service": service,
                "original_provider": provider
            }
            
            # Obtener handler desde factory con credenciales
            return get_discovery_handler(handler_name, extended_credentials)
                    
        except ImportError:
            self.logger.debug(f"Discovery handler for {provider} not available")
            return None
    
    def _get_handler_name(self, provider: str, service: Optional[str]) -> str:
        """
        Construye nombre de handler dinámicamente sin hardcodeo
        """
        from app.handlers.discovery.discovery_factory import list_available_handlers
        
        # Obtener handlers registrados dinámicamente
        available_handlers = list_available_handlers()
        
        # Lista de nombres posibles en orden de prioridad
        possible_names = []
        
        provider_lower = provider.lower()
        
        # Si hay service, intentar combinaciones específicas PRIMERO
        if service:
            service_lower = service.lower()
            possible_names.extend([
                service_lower,                    # gmail, sheets, drive - MÁS ESPECÍFICO PRIMERO
                f"{provider_lower}_{service_lower}",  # google_gmail, google_sheets  
                f"{provider_lower}{service_lower}",   # googlegmail, googlesheets
                f"{service_lower}_{provider_lower}",  # gmail_google
            ])
        
        # Solo agregar provider genérico al final como último recurso
        possible_names.append(provider_lower)  # google, dropbox
        
        # Buscar primer handler disponible
        for name in possible_names:
            if name in available_handlers:
                self.logger.debug(f"Found handler: {name} for {provider}/{service}")
                return name
        
        # Si no encuentra nada, usar provider como fallback
        self.logger.warning(f"No specific handler found for {provider}/{service}, using {provider_lower}")
        return provider_lower
    
    def _create_discovered_file(
        self, 
        file_data: Dict[str, Any], 
        provider: str
    ) -> Optional[DiscoveredFile]:
        """
        Crea DiscoveredFile desde datos del connector
        """
        try:
            return DiscoveredFile(
                id=file_data.get("id", ""),
                name=file_data.get("name", ""),
                provider=provider,
                file_type=file_data.get("type", "unknown"),
                confidence=file_data.get("confidence", 0.8),
                structure=file_data.get("structure", {}),
                icon=file_data.get("icon", "📄"),
                metadata=file_data.get("metadata", {})
            )
        except Exception as e:
            self.logger.warning(f"Error creating discovered file: {e}")
            return None


def get_file_discovery_service(
    credential_service: CredentialService = Depends(get_credential_service),
    auth_resolver: CentralAuthResolver = Depends(get_auth_resolver)
) -> FileDiscoveryService:
    """
    🔥 SEPARACIÓN LIMPIA: Factory function para file discovery dependency injection
    Usa CredentialService para credenciales y AuthResolver para auth policy
    """
    return FileDiscoveryService(
        credential_service=credential_service,
        auth_resolver=auth_resolver
    )