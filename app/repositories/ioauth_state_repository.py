# app/repositories/ioauth_state_repository.py

from abc import ABC, abstractmethod
from typing import Optional


class IOAuthStateRepository(ABC):
    """
    Interfaz para el repositorio de estados OAuth (anti-CSRF).
    """

    @abstractmethod
    async def save_oauth_state(self, user_id: int, provider: str, state: str) -> None:
        """
        Guarda o actualiza el state generado para el user_id+provider.
        """
        ...

    @abstractmethod
    async def get_oauth_state(self, user_id: int, provider: str) -> Optional[str]:
        """
        Recupera el state previamente guardado para user_id+provider.
        Retorna None si no existe.
        """
        ...

    @abstractmethod
    async def delete_oauth_state(self, user_id: int, provider: str) -> None:
        """
        Elimina el state usado para user_id+provider.
        """
        ...
