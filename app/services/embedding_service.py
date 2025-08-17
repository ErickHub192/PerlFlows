# app/services/embedding_service.py

# Servicio de embeddings usado para búsquedas semánticas.
# Actualmente no existe un agente de Retrieval-Augmented Generation (RAG)
# integrado; este módulo simplemente expone utilidades de búsqueda.

import asyncio
from typing import List, Tuple
from openai import OpenAI
from numpy import dot
from numpy.linalg import norm
from fastapi import Depends

from app.services.IEmbeddingService import IEmbeddingService
from app.repositories.node_repository import NodeRepository

class EmbeddingService(IEmbeddingService):
    def __init__(self, repo: NodeRepository, openai_client: OpenAI, metric: str = "cosine"):
        self.repo = repo
        self.openai = openai_client
        self.metric = metric  # "cosine" o "l2"
        self._cache: List[Tuple[str, List[float]]] | None = None

    async def _load_cache(self):
        """Precarga embeddings de la BD en memoria."""
        items = self.repo.list_embeddings()  # List[(UUID, List[float])]
        self._cache = [(str(node_id), emb) for node_id, emb in items]

    async def search(self, query: str, top_n: int = 5) -> List[Tuple[str, float]]:
        if self._cache is None:
            await self._load_cache()

        # 1) Obtener embedding de la consulta
        resp = await asyncio.to_thread(
            lambda: self.openai.embeddings.create(
                model="text-embedding-3-small", input=query
            )
        )
        q_vec = resp["data"][0]["embedding"]

        # 2) Auto‑switch a cosine si el vector no está normalizado y estamos en L2
        norm_q = norm(q_vec)
        if self.metric == "l2" and not (0.9 <= norm_q <= 1.1):
            self.metric = "cosine"

        # 3) Calcular puntuaciones
        sims: List[Tuple[str, float]] = []
        for node_id, vec in self._cache:
            if self.metric == "cosine":
                score = dot(q_vec, vec) / (norm_q * norm(vec))
            else:  # l2
                # Distancia Euclídea → invertimos para que 'más cercano' sea mayor score
                dist = norm([a - b for a, b in zip(q_vec, vec)])
                score = -dist
            sims.append((node_id, float(score)))

        # 4) Ordenar descendentemente y devolver top_n
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_n]


async def get_embedding_service(
    repo: NodeRepository = Depends(),  # Necesita factory del repo
    openai_client: OpenAI = Depends(),  # Necesita factory del cliente
    metric: str = "cosine"
) -> IEmbeddingService:
    """
    Factory para inyectar EmbeddingService en FastAPI
    """
    return EmbeddingService(repo, openai_client, metric)
