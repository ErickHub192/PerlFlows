# app/ai/llm_clients/provider_registry.py
"""
LLM Provider Registry - Registro simple y modular de proveedores
Cada proveedor define sus propios modelos, sin hardcoding en el router
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class ModelOption:
    """Opción de modelo para dropdown"""
    id: str
    name: str
    description: str
    recommended: bool = False
    is_default: bool = False

@dataclass 
class ProviderInfo:
    """Información de un proveedor LLM"""
    id: str
    name: str
    description: str
    api_key_format: str
    website: str
    pricing_url: str
    models: List[ModelOption]
    capabilities: List[str]

class LLMProvider(ABC):
    """Interfaz base para proveedores LLM"""
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """ID único del proveedor"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre display del proveedor"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción del proveedor"""
        pass
    
    @property
    @abstractmethod
    def api_key_format(self) -> str:
        """Formato esperado de la API key"""
        pass
    
    @property
    @abstractmethod
    def website(self) -> str:
        """Website del proveedor"""
        pass
    
    @property
    @abstractmethod
    def pricing_url(self) -> str:
        """URL de pricing"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[ModelOption]:
        """Retorna modelos disponibles para este proveedor"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Retorna capacidades del proveedor"""
        pass
    
    def get_default_model(self) -> Optional[str]:
        """Retorna modelo por defecto"""
        models = self.get_available_models()
        for model in models:
            if model.is_default:
                return model.id
        return models[0].id if models else None

class ProviderRegistry:
    """Registro de proveedores LLM"""
    
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
    
    def register(self, provider: LLMProvider):
        """Registra un proveedor"""
        self._providers[provider.provider_id] = provider
        logger.info(f"Registered LLM provider: {provider.provider_name}")
    
    def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        """Obtiene un proveedor por ID"""
        return self._providers.get(provider_id)
    
    def get_all_providers(self) -> Dict[str, ProviderInfo]:
        """Obtiene información de todos los proveedores"""
        providers_info = {}
        
        for provider_id, provider in self._providers.items():
            providers_info[provider_id] = ProviderInfo(
                id=provider.provider_id,
                name=provider.provider_name,
                description=provider.description,
                api_key_format=provider.api_key_format,
                website=provider.website,
                pricing_url=provider.pricing_url,
                models=provider.get_available_models(),
                capabilities=provider.get_capabilities()
            )
        
        return providers_info
    
    def get_supported_provider_ids(self) -> List[str]:
        """Obtiene lista de IDs de proveedores soportados"""
        return list(self._providers.keys())

# Instancia global
provider_registry = ProviderRegistry()