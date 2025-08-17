# app/services/IEmbeddingService.py

from abc import ABC, abstractmethod
from typing import List, Tuple


class IEmbeddingService(ABC):
    """
    Interface para el servicio de embeddings.
    Usado para búsquedas semánticas y operaciones de Retrieval-Augmented Generation (RAG).
    """

    @abstractmethod
    async def search(self, query: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Busca los embeddings más similares a la query.
        
        Args:
            query: Texto de consulta para buscar
            top_n: Número de resultados más similares a devolver
            
        Returns:
            Lista de tuplas (node_id, similarity_score) ordenadas por similitud
        """
        pass

