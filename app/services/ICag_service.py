# app/services/ICag_service.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ICAGService(ABC):
    """
    🔥 OPCIÓN 2: Interfaz para Redis-First Node Cache Service.
    
    Define métodos para:
    - Inicializar cache Redis desde BD (startup)
    - Acceder instantáneamente desde cache (function tools)
    - Fallback a BD solo en emergencias
    """

    @abstractmethod
    async def build_context(self) -> List[Dict[str, Any]]:
        """
        🔧 Accede instantáneamente a nodos desde Redis cache.
        Fallback a construcción BD solo en cache miss crítico.

        Returns:
            Lista de nodos/servicios desde Redis cache
        """
        ...
    
    @abstractmethod  
    async def initialize_cache_from_db(self) -> bool:
        """
        🚀 STARTUP: Inicializa cache Redis con metadatos desde Supabase.
        Solo se ejecuta una vez al arrancar la aplicación.

        Returns:
            True si inicialización exitosa
        """
        ...
