# app/ai/llm_clients/protocol.py

from typing import Protocol, Any, List, Dict

class LLMClientProtocol(Protocol):
    """
    Interfaz genérica para clientes de LLM.

    Métodos requeridos:
      • chat_completion(messages, temperature=0.0, **kwargs) → Any  
        Envía una solicitud de finalización de chat.
        :param messages: Lista de dicts con 'role' y 'content'.
        :param temperature: Control de aleatoriedad en [0,1].
        :param kwargs: Argumentos adicionales (kv_cache, use_cache, etc.).
        :return: Respuesta cruda del LLM.

    Métodos opcionales:
    • can_handle_model(model: str) → bool  
        Indica si el cliente soporta el identificador de modelo.
    • export_kv_cache() → bytes  
        Extrae el blob de KV-cache tras una llamada con use_cache=True.
    • load_kv_cache(kv_bytes: bytes) → None  
        Carga el KV-cache en el cliente.
    """
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        **kwargs : Any
    ) -> Any:
        ...

    async def embed(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Genera embeddings para una lista de textos.
        :param texts: lista de cadenas a vectorizar.
        :param model: identificador del modelo de embedding.
        :return: lista de vectores (uno por texto).
        """
        ...

    @staticmethod
    def can_handle_model(cls, model: str) -> bool:
        ...
    
    def export_kv_cache(self) -> bytes:
        ...

    def load_kv_cache(self, kv_bytes: bytes) -> None:
        ...    
