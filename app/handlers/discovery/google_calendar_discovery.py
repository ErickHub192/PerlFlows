"""
Google Calendar Discovery Handler
Descubre calendarios, eventos, y recursos en Google Calendar
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError

from app.handlers.discovery.discovery_factory import register_discovery_handler
from app.handlers.discovery.base_google_discovery import BaseGoogleDiscoveryHandler

logger = logging.getLogger(__name__)


@register_discovery_handler("google_calendar", "calendar", "gcalendar")
class GoogleCalendarDiscoveryHandler(BaseGoogleDiscoveryHandler):
    """
    Discovery handler para Google Calendar
    Puede descubrir calendarios, eventos, y recursos de calendario
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, service_name='calendar')
    
    async def discover_files(
        self, 
        file_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Descubre calendarios como "archivos"
        """
        try:
            calendar_service = await self.get_main_service()
            
            # Listar calendarios del usuario
            calendar_list = calendar_service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            discovered_calendars = []
            for calendar in calendars[:limit]:
                calendar_info = await self._format_calendar_as_file(calendar)
                discovered_calendars.append(calendar_info)
            
            self.logger.info(f"Discovered {len(discovered_calendars)} calendars")
            return discovered_calendars
            
        except HttpError as e:
            self.logger.error(f"Google Calendar API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering Google Calendar: {e}")
            return []
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadata detallada de un calendario específico
        """
        try:
            calendar_service = await self.get_main_service()
            
            calendar = calendar_service.calendars().get(calendarId=file_id).execute()
            
            return await self._format_detailed_calendar(calendar_service, calendar)
            
        except HttpError as e:
            self.logger.error(f"Error getting calendar metadata: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error getting calendar metadata: {e}")
            return {}
    
    async def discover_events(
        self, 
        calendar_id: str = 'primary',
        days_ahead: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Descubre eventos en un calendario específico
        """
        try:
            calendar_service = await self.get_main_service()
            
            # Configurar rango de tiempo
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=limit,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                event_info = await self._format_event_as_file(event, calendar_id)
                formatted_events.append(event_info)
            
            return formatted_events
            
        except Exception as e:
            self.logger.error(f"Error discovering calendar events: {e}")
            return []
    
    async def discover_busy_times(
        self, 
        calendar_ids: List[str] = None,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Descubre horarios ocupados usando freebusy API
        """
        try:
            calendar_service = await self.get_main_service()
            
            if not calendar_ids:
                calendar_ids = ['primary']
            
            # Configurar rango de tiempo
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }
            
            freebusy = calendar_service.freebusy().query(body=body).execute()
            
            return {
                "time_range": {"start": time_min, "end": time_max},
                "calendars": freebusy.get('calendars', {}),
                "summary": self._summarize_busy_times(freebusy.get('calendars', {}))
            }
            
        except Exception as e:
            self.logger.error(f"Error discovering busy times: {e}")
            return {}
    
    async def _format_calendar_as_file(self, calendar: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatea calendario como archivo
        """
        access_role = calendar.get('accessRole', 'reader')
        is_primary = calendar.get('primary', False)
        
        # Determinar tipo de calendario
        cal_type = "calendar"
        if is_primary:
            cal_type = "primary_calendar"
        elif access_role == "owner":
            cal_type = "owned_calendar"
        elif access_role in ["reader", "freeBusyReader"]:
            cal_type = "shared_calendar"
        
        structure = {
            "type": cal_type,
            "is_primary": is_primary,
            "access_role": access_role,
            "can_create_events": access_role in ["owner", "writer"],
            "can_modify_events": access_role in ["owner", "writer"],
            "timezone": calendar.get('timeZone', 'UTC')
        }
        
        metadata = {
            "summary": calendar.get('summary', ''),
            "description": calendar.get('description', ''),
            "timezone": calendar.get('timeZone', 'UTC'),
            "access_role": access_role,
            "color_id": calendar.get('colorId'),
            "background_color": calendar.get('backgroundColor'),
            "foreground_color": calendar.get('foregroundColor'),
            "selected": calendar.get('selected', False),
            "notifications": calendar.get('defaultReminders', [])
        }
        
        return self._format_file_info(
            file_id=calendar['id'],
            name=calendar.get('summary', 'Unnamed Calendar'),
            file_type=cal_type,
            structure=structure,
            icon='📅',
            metadata=metadata,
            mime_type='text/calendar'
        )
    
    async def _format_detailed_calendar(self, service, calendar: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatea información detallada del calendario incluyendo estadísticas
        """
        calendar_id = calendar['id']
        
        # Obtener eventos recientes para estadísticas
        try:
            now = datetime.utcnow()
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=now.isoformat() + 'Z',
                maxResults=100,
                singleEvents=True
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calcular estadísticas
            upcoming_events = len(events)
            has_recurring = any(event.get('recurrence') for event in events)
            
        except Exception:
            upcoming_events = 0
            has_recurring = False
        
        return {
            "id": calendar['id'],
            "summary": calendar.get('summary', ''),
            "description": calendar.get('description', ''),
            "timezone": calendar.get('timeZone', 'UTC'),
            "location": calendar.get('location', ''),
            "etag": calendar.get('etag', ''),
            "statistics": {
                "upcoming_events": upcoming_events,
                "has_recurring_events": has_recurring
            },
            "conference_properties": calendar.get('conferenceProperties', {}),
            "next_sync_token": calendar.get('nextSyncToken')
        }
    
    async def _format_event_as_file(self, event: Dict[str, Any], calendar_id: str) -> Dict[str, Any]:
        """
        Formatea evento como archivo
        """
        event_type = "event"
        
        # Determinar tipo de evento
        if event.get('recurrence'):
            event_type = "recurring_event"
        elif event.get('attendees'):
            event_type = "meeting_event"
        elif event.get('hangoutLink') or event.get('conferenceData'):
            event_type = "conference_event"
        
        # Información de tiempo
        start = event.get('start', {})
        end = event.get('end', {})
        
        is_all_day = 'date' in start  # All-day events use 'date' instead of 'dateTime'
        
        structure = {
            "type": event_type,
            "is_all_day": is_all_day,
            "has_attendees": bool(event.get('attendees')),
            "has_attachments": bool(event.get('attachments')),
            "has_conference": bool(event.get('hangoutLink') or event.get('conferenceData')),
            "is_recurring": bool(event.get('recurrence')),
            "calendar_id": calendar_id
        }
        
        metadata = {
            "summary": event.get('summary', ''),
            "description": event.get('description', ''),
            "location": event.get('location', ''),
            "start_time": start.get('dateTime') or start.get('date'),
            "end_time": end.get('dateTime') or end.get('date'),
            "creator": event.get('creator', {}),
            "organizer": event.get('organizer', {}),
            "attendees": event.get('attendees', []),
            "status": event.get('status', 'confirmed'),
            "visibility": event.get('visibility', 'default'),
            "hangout_link": event.get('hangoutLink'),
            "html_link": event.get('htmlLink')
        }
        
        return self._format_file_info(
            file_id=event['id'],
            name=event.get('summary', 'Untitled Event'),
            file_type=event_type,
            structure=structure,
            icon='📅',
            metadata=metadata,
            created=event.get('created'),
            modified=event.get('updated'),
            mime_type='text/calendar'
        )
    
    def _summarize_busy_times(self, calendars_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume horarios ocupados de múltiples calendarios
        """
        total_busy_periods = 0
        total_busy_duration = 0
        
        for cal_id, cal_data in calendars_data.items():
            busy_periods = cal_data.get('busy', [])
            total_busy_periods += len(busy_periods)
            
            # Calcular duración total (aproximada)
            for period in busy_periods:
                try:
                    start = datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
                    duration = (end - start).total_seconds() / 3600  # horas
                    total_busy_duration += duration
                except Exception:
                    continue
        
        return {
            "total_busy_periods": total_busy_periods,
            "total_busy_hours": round(total_busy_duration, 2),
            "calendars_checked": len(calendars_data)
        }