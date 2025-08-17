# app/repositories/login_repository.py

import asyncio
from supabase import Client
from typing import Optional, Dict, Any

class LoginRepository:
    def __init__(self, client: Client):
        self.supabase = client

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        def _sync():
            resp = (
                self.supabase
                .table("users")
                .insert(data)
                .execute()
            )
            return resp.data if hasattr(resp, "data") else resp[0]
        return await asyncio.to_thread(_sync)

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        def _sync():
            resp = (
                self.supabase
                .table("users")
                .select("*")
                .eq("username", username)
                .execute()
            )
            return resp.data[0] if resp.data else None
        return await asyncio.to_thread(_sync)

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        def _sync():
            resp = (
                self.supabase
                .table("users")
                .update(data)
                .eq("id", user_id)
                .execute()
            )
            return resp.data[0] if resp.data else {}
        return await asyncio.to_thread(_sync)

    async def delete_user(self, user_id: int) -> None:
        def _sync():
            self.supabase \
                .table("users") \
                .delete() \
                .eq("id", user_id) \
                .execute()
        await asyncio.to_thread(_sync)

