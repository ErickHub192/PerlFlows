"""
Base Google Discovery Handler
Usa Google Discovery Service para auto-descubrir servicios y métodos
Elimina hardcoded service names y versions
"""
import logging
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.handlers.discovery.discovery_factory import BaseDiscoveryHandler

logger = logging.getLogger(__name__)


class BaseGoogleDiscoveryHandler(BaseDiscoveryHandler):
    """
    Base class para Google discovery handlers que usa Google Discovery Service
    Auto-descubre servicios disponibles y sus versiones más recientes
    """
    
    def __init__(self, credentials: Dict[str, Any], service_name: str):
        super().__init__(credentials)
        self.service_name = service_name
        
        # Limpiar credenciales de metadata - solo campos válidos para Google Credentials
        valid_fields = {"token", "refresh_token", "id_token", "token_uri", "client_id", "client_secret", "scopes"}
        clean_creds = {k: v for k, v in credentials.items() if k in valid_fields and v is not None}
        
        # Si no hay token, usar access_token como token
        if "access_token" in credentials and "token" not in clean_creds:
            clean_creds["token"] = credentials["access_token"]
        
        # ✅ FIX: Asegurar campos OAuth obligatorios para refresh tokens
        # Si falta algún campo crítico, usar valores por defecto de Google OAuth
        if not clean_creds.get("token_uri"):
            clean_creds["token_uri"] = "https://oauth2.googleapis.com/token"
        
        # ✅ FIX: Si no hay refresh_token, log warning pero continuar sin refresh
        if not clean_creds.get("refresh_token"):
            logger.warning(f"⚠️ OAuth credentials for {service_name} missing refresh_token - tokens won't auto-refresh")
            logger.warning(f"Available credential fields: {list(credentials.keys())}")
        
        # ✅ FIX: Si no hay client_id/client_secret, log warning pero continuar 
        if not clean_creds.get("client_id") or not clean_creds.get("client_secret"):
            logger.warning(f"⚠️ OAuth credentials for {service_name} missing client_id/client_secret - refresh may fail")
            logger.debug(f"Has client_id: {'client_id' in clean_creds}, Has client_secret: {'client_secret' in clean_creds}")
        
        try:
            self.google_creds = Credentials(**clean_creds)
            logger.info(f"✅ Google credentials initialized for {service_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google credentials for {service_name}: {e}")
            logger.error(f"Clean credentials used: {list(clean_creds.keys())}")
            raise
        self.discovery_service = None
        self.service_info = None
        self.main_service = None
        
        # Cache de servicios ya construidos
        self._service_cache = {}
    
    async def _init_discovery_service(self):
        """Inicializa el servicio de discovery de Google"""
        if not self.discovery_service:
            try:
                self.discovery_service = build('discovery', 'v1', credentials=self.google_creds)
                await self._discover_service_info()
            except Exception as e:
                logger.error(f"Error initializing Google Discovery Service: {e}")
                # Fallback a versiones hardcoded
                self.service_info = {"version": "v3"}  # Default fallback
    
    async def _discover_service_info(self):
        """Descubre información del servicio usando Google Discovery API"""
        try:
            # Listar todas las APIs disponibles
            apis_result = self.discovery_service.apis().list().execute()
            apis = apis_result.get('items', [])
            
            # Buscar nuestro servicio
            service_apis = [api for api in apis if api.get('name') == self.service_name]
            
            if service_apis:
                # Usar la versión más reciente (asumiendo que están ordenadas)
                latest_api = max(service_apis, key=lambda x: x.get('version', ''))
                
                self.service_info = {
                    "name": latest_api.get('name'),
                    "version": latest_api.get('version'),
                    "title": latest_api.get('title'),
                    "description": latest_api.get('description'),
                    "discovery_link": latest_api.get('discoveryLink'),
                    "preferred": latest_api.get('preferred', False)
                }
                
                logger.info(f"Discovered {self.service_name} v{self.service_info['version']}")
            else:
                logger.warning(f"Service {self.service_name} not found in discovery")
                # Fallback a versiones conocidas
                fallback_versions = {
                    'drive': 'v3',
                    'sheets': 'v4', 
                    'gmail': 'v1',
                    'calendar': 'v3'
                }
                self.service_info = {"version": fallback_versions.get(self.service_name, "v1")}
                
        except Exception as e:
            logger.error(f"Error discovering service info for {self.service_name}: {e}")
            # Fallback básico
            self.service_info = {"version": "v1"}
    
    async def _get_service(self, service_name: str = None, version: str = None):
        """
        Obtiene servicio de Google APIs con discovery automático
        
        Args:
            service_name: Nombre del servicio (usa self.service_name si no se especifica)
            version: Versión específica (usa discovered version si no se especifica)
        """
        service_name = service_name or self.service_name
        
        # Cache key
        cache_key = f"{service_name}_{version or 'auto'}"
        
        if cache_key in self._service_cache:
            return self._service_cache[cache_key]
        
        # Inicializar discovery si no está listo
        if not self.service_info:
            await self._init_discovery_service()
        
        # Determinar versión
        if not version:
            version = self.service_info.get('version', 'v1')
        
        try:
            # ✅ FIX: Validar credenciales antes de construir servicio
            if not self.google_creds.token:
                logger.error(f"❌ No access token available for {service_name}")
                raise Exception(f"No access token available for {service_name}")
            
            # ✅ FIX: Si el token está expirado y tenemos refresh_token, intentar refresh
            if self.google_creds.expired and self.google_creds.refresh_token:
                logger.info(f"🔄 Token expired for {service_name}, attempting refresh...")
                try:
                    from google.auth.transport.requests import Request
                    self.google_creds.refresh(Request())
                    logger.info(f"✅ Token refreshed successfully for {service_name}")
                except Exception as refresh_error:
                    logger.error(f"❌ Token refresh failed for {service_name}: {refresh_error}")
                    # Continuar con token expirado, puede que funcione
            elif self.google_creds.expired:
                logger.warning(f"⚠️ Token expired for {service_name} but no refresh_token available")
            
            # Construir servicio
            service = build(service_name, version, credentials=self.google_creds)
            
            # Cache it
            self._service_cache[cache_key] = service
            
            logger.debug(f"Built Google service: {service_name} v{version}")
            return service
            
        except Exception as e:
            logger.error(f"Error building Google service {service_name} v{version}: {e}")
            # ✅ FIX: Si es error de credenciales, dar mensaje más específico
            if "credentials" in str(e).lower() or "oauth" in str(e).lower():
                logger.error(f"💡 Hint: May need to re-authorize {service_name} OAuth access")
            raise
    
    async def get_main_service(self):
        """Obtiene el servicio principal para este handler"""
        if not self.main_service:
            self.main_service = await self._get_service()
        return self.main_service
    
    async def get_drive_service(self):
        """Helper para obtener servicio de Drive (común en muchos handlers)"""
        return await self._get_service('drive')
    
    async def get_sheets_service(self):
        """Helper para obtener servicio de Sheets"""
        return await self._get_service('sheets')
    
    async def get_gmail_service(self):
        """Helper para obtener servicio de Gmail"""
        return await self._get_service('gmail')
    
    async def get_calendar_service(self):
        """Helper para obtener servicio de Calendar"""
        return await self._get_service('calendar')
    
    def get_service_info(self) -> Dict[str, Any]:
        """Retorna información descubierta del servicio"""
        return self.service_info or {}
    
    async def discover_available_methods(self) -> List[Dict[str, Any]]:
        """
        Descubre métodos disponibles para el servicio usando Discovery API
        """
        try:
            if not self.discovery_service:
                await self._init_discovery_service()
            
            if not self.service_info or not self.service_info.get('discovery_link'):
                return []
            
            # Obtener document de discovery para el servicio
            discovery_doc = self.discovery_service.apis().getRest(
                api=self.service_name,
                version=self.service_info.get('version')
            ).execute()
            
            methods = []
            resources = discovery_doc.get('resources', {})
            
            # Recursivamente extraer métodos de recursos
            self._extract_methods_from_resources(resources, methods)
            
            return methods
            
        except Exception as e:
            logger.error(f"Error discovering methods for {self.service_name}: {e}")
            return []
    
    def _extract_methods_from_resources(self, resources: Dict, methods: List, path: str = ""):
        """Extrae métodos recursivamente de recursos de discovery"""
        for resource_name, resource_data in resources.items():
            current_path = f"{path}.{resource_name}" if path else resource_name
            
            # Métodos directos en este recurso
            resource_methods = resource_data.get('methods', {})
            for method_name, method_data in resource_methods.items():
                methods.append({
                    'path': f"{current_path}.{method_name}",
                    'http_method': method_data.get('httpMethod'),
                    'description': method_data.get('description'),
                    'parameters': method_data.get('parameters', {}),
                    'scopes': method_data.get('scopes', [])
                })
            
            # Recursos nested
            nested_resources = resource_data.get('resources', {})
            if nested_resources:
                self._extract_methods_from_resources(nested_resources, methods, current_path)