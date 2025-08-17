"""
Gmail Discovery Handler
Descubre emails, labels, y threads en Gmail del usuario
"""
import logging
from typing import Dict, Any, List, Optional
from googleapiclient.errors import HttpError

from .discovery_factory import register_discovery_handler
from .base_google_discovery import BaseGoogleDiscoveryHandler

logger = logging.getLogger(__name__)


@register_discovery_handler("gmail", "google_gmail", "gmail_discovery")
class GmailDiscoveryHandler(BaseGoogleDiscoveryHandler):
    """
    Discovery handler para Gmail
    Puede descubrir emails, labels, threads, etc.
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, service_name='gmail')
    
    async def discover_files(
        self, 
        file_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Descubre emails en Gmail (interpretando emails como "archivos")
        También incluye información del usuario autenticado
        """
        try:
            gmail_service = await self.get_main_service()
            
            discovered_items = []
            
            # 🔥 NUEVO: Obtener información del usuario autenticado
            user_profile = await self._get_authenticated_user_profile(gmail_service)
            if user_profile:
                discovered_items.append(user_profile)
            
            # Construir query para mensajes
            query = ""
            if file_types:
                # Mapear tipos a queries de Gmail
                if "unread" in file_types:
                    query = "is:unread"
                elif "important" in file_types:
                    query = "is:important"
                elif "attachments" in file_types:
                    query = "has:attachment"
            
            # Buscar mensajes
            results = gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(limit, 100)
            ).execute()
            
            messages = results.get('messages', [])
            
            # Formatear mensajes como "archivos"
            for msg in messages[:limit]:  # Limitar procesamiento
                email_info = await self._format_email_message(gmail_service, msg['id'])
                if email_info:
                    discovered_items.append(email_info)
            
            self.logger.info(f"Discovered {len(discovered_items)} items in Gmail (including user profile)")
            return discovered_items
            
        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering Gmail messages: {e}")
            return []
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadata detallada de un email específico
        """
        try:
            gmail_service = await self.get_main_service()
            
            message = gmail_service.users().messages().get(
                userId='me',
                id=file_id,
                format='full'
            ).execute()
            
            return await self._format_detailed_email(message)
            
        except HttpError as e:
            self.logger.error(f"Error getting email metadata: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error getting email metadata: {e}")
            return {}
    
    async def discover_labels(self) -> List[Dict[str, Any]]:
        """
        Descubre labels disponibles en Gmail
        """
        try:
            gmail_service = await self.get_main_service()
            
            results = gmail_service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            formatted_labels = []
            for label in labels:
                formatted_labels.append({
                    "id": label['id'],
                    "name": label['name'],
                    "type": label.get('type', 'user'),
                    "messages_total": label.get('messagesTotal', 0),
                    "messages_unread": label.get('messagesUnread', 0),
                    "threads_total": label.get('threadsTotal', 0),
                    "threads_unread": label.get('threadsUnread', 0)
                })
            
            return formatted_labels
            
        except Exception as e:
            self.logger.error(f"Error discovering Gmail labels: {e}")
            return []
    
    async def _get_authenticated_user_profile(self, gmail_service) -> Dict[str, Any]:
        """
        🔥 NUEVO: Obtiene información del usuario autenticado
        Esto incluye su email address que se usa automáticamente como remitente
        """
        try:
            # Obtener perfil del usuario autenticado
            profile = gmail_service.users().getProfile(userId='me').execute()
            
            email_address = profile.get('emailAddress', '')
            messages_total = profile.get('messagesTotal', 0)
            threads_total = profile.get('threadsTotal', 0)
            
            # Formatear como "archivo" especial de tipo user_profile
            user_profile_info = {
                "id": "authenticated_user_profile",
                "name": f"Usuario autenticado: {email_address}",
                "file_type": "user_profile",
                "provider": "gmail",
                "confidence": 1.0,
                "icon": "👤",
                "structure": {
                    "type": "user_profile",
                    "is_authenticated": True,
                    "can_send_as": True,
                    "default_sender": True
                },
                "metadata": {
                    "email_address": email_address,
                    "messages_total": messages_total,
                    "threads_total": threads_total,
                    "history_id": profile.get('historyId'),
                    "gmail_user_id": profile.get('emailAddress'),
                    "discovery_type": "authenticated_user",
                    "usage_hint": "Este email se usará automáticamente como remitente"
                }
            }
            
            self.logger.info(f"🔥 DISCOVERED AUTHENTICATED USER: {email_address}")
            return user_profile_info
            
        except HttpError as e:
            # ✅ FIX: Error handling más específico para problemas OAuth
            if "credentials" in str(e).lower() or "refresh" in str(e).lower():
                self.logger.warning(f"⚠️ Gmail OAuth credentials issue - may need re-authorization: {e}")
                # Return fallback profile instead of failing completely
                return {
                    "id": "gmail_auth_needed",
                    "name": "Gmail (Re-authorization Required)",
                    "file_type": "auth_warning",
                    "provider": "gmail",
                    "confidence": 0.1,
                    "icon": "🔐",
                    "structure": {
                        "type": "auth_warning",
                        "needs_reauth": True
                    },
                    "metadata": {
                        "error": "OAuth credentials need refresh",
                        "discovery_type": "auth_warning",
                        "usage_hint": "Please re-authorize Gmail access"
                    }
                }
            else:
                self.logger.error(f"Error getting authenticated user profile: {e}")
                return None
        except Exception as e:
            # ✅ FIX: Capturar errores de refresh token específicamente
            if "refresh" in str(e).lower() or "token" in str(e).lower():
                self.logger.warning(f"⚠️ Gmail token refresh issue: {e}")
                return {
                    "id": "gmail_token_issue",
                    "name": "Gmail (Token Issue)",
                    "file_type": "auth_warning", 
                    "provider": "gmail",
                    "confidence": 0.1,
                    "icon": "⚠️",
                    "structure": {
                        "type": "auth_warning",
                        "needs_reauth": True
                    },
                    "metadata": {
                        "error": str(e),
                        "discovery_type": "token_warning",
                        "usage_hint": "Gmail access may be limited due to token issues"
                    }
                }
            else:
                self.logger.error(f"Error getting authenticated user profile: {e}")
                return None
    
    async def _format_email_message(self, service, message_id: str) -> Dict[str, Any]:
        """
        Formatea mensaje de Gmail como archivo
        """
        try:
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
            
            # Determinar tipo de email
            email_type = "email"
            has_attachments = False
            
            payload = message.get('payload', {})
            if payload.get('parts'):
                for part in payload['parts']:
                    if part.get('filename'):
                        has_attachments = True
                        break
            
            if has_attachments:
                email_type = "email_with_attachments"
            
            structure = {
                "type": email_type,
                "has_attachments": has_attachments,
                "is_read": 'UNREAD' not in message.get('labelIds', []),
                "is_important": 'IMPORTANT' in message.get('labelIds', []),
                "thread_id": message.get('threadId')
            }
            
            metadata = {
                "from": headers.get('From', ''),
                "subject": headers.get('Subject', ''),
                "date": headers.get('Date', ''),
                "labels": message.get('labelIds', []),
                "snippet": message.get('snippet', ''),
                "gmail_id": message['id']
            }
            
            return self._format_file_info(
                file_id=message['id'],
                name=headers.get('Subject', 'No Subject'),
                file_type=email_type,
                structure=structure,
                icon='📧',
                metadata=metadata,
                created=headers.get('Date'),
                mime_type='message/rfc822'
            )
            
        except Exception as e:
            self.logger.error(f"Error formatting email message {message_id}: {e}")
            return None
    
    async def _format_detailed_email(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatea información detallada de un email
        """
        headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
        
        # Extraer attachments
        attachments = []
        payload = message.get('payload', {})
        
        def extract_attachments(parts):
            for part in parts:
                if part.get('filename'):
                    attachments.append({
                        "filename": part['filename'],
                        "mime_type": part.get('mimeType'),
                        "size": part.get('body', {}).get('size', 0),
                        "attachment_id": part.get('body', {}).get('attachmentId')
                    })
                elif part.get('parts'):
                    extract_attachments(part['parts'])
        
        if payload.get('parts'):
            extract_attachments(payload['parts'])
        
        return {
            "id": message['id'],
            "thread_id": message.get('threadId'),
            "subject": headers.get('Subject', ''),
            "from": headers.get('From', ''),
            "to": headers.get('To', ''),
            "cc": headers.get('Cc', ''),
            "date": headers.get('Date', ''),
            "labels": message.get('labelIds', []),
            "snippet": message.get('snippet', ''),
            "attachments": attachments,
            "size_estimate": message.get('sizeEstimate', 0),
            "is_read": 'UNREAD' not in message.get('labelIds', []),
            "is_important": 'IMPORTANT' in message.get('labelIds', []),
            "is_starred": 'STARRED' in message.get('labelIds', [])
        }