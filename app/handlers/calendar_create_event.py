# app/connectors/handlers/calendar_create_event.py

import time
from typing import Dict, Any
from .base_google_action_handler import BaseGoogleActionHandler
from app.connectors.factory import register_node, register_tool

@register_node("Google_Calendar.create_event")
@register_tool("Google_Calendar.create_event")
class CalendarCreateEventHandler(BaseGoogleActionHandler):
    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds, service_name='calendar')

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.perf_counter()
        # ✅ Servicio con auto-discovery
        service = await self.get_main_service()

        event = {
            "summary":     params["summary"],
            "description": params.get("description"),
            "start":      {"dateTime": params["start"]},
            "end":        {"dateTime": params["end"]},
        }

        created = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        return {
            "status":      "success",
            "output":      created,
            "duration_ms": int((time.perf_counter() - start_time)*1000)
        }
