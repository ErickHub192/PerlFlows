# app/connectors/gmail_send_message.py

import time
import base64
from typing import Any, Dict
from email.mime.text import MIMEText
from app.connectors.factory import register_tool, register_node
from app.handlers.base_google_action_handler import BaseGoogleActionHandler
from app.exceptions.logging_utils import get_kyra_logger


@register_node("Gmail.send_messages")
@register_tool("Gmail.send_messages")
class GmailSendMessageHandler(BaseGoogleActionHandler):
    """
    Handler que manda un correo via Gmail API.
    Se usa como tool desde ToolRouter/ToolExecutor.
    """

    def __init__(self):
        """
        Constructor sin credenciales - se pasan en execute()
        """
        # Don't call super().__init__() with creds here - they come in execute()
        self.logger = get_kyra_logger(__name__)

    async def execute(
        self,
        params: Dict[str, Any],
        creds: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        :param params: {
            "from":   str,    # opcional, default "me"
            "to":     str,    # correo destino
            "subject": str,   # asunto
            "body":   str     # texto del mensaje
        }
        :return: {status, output, duration_ms[, error]}
        """
        start = time.perf_counter()
        
        # 🔧 Get credentials from params
        if 'creds' in params:
            creds = params['creds']
        
        if not creds:
            return {
                "status": "error",
                "output": None,
                "error": "No credentials provided",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }
        
        # 🔧 Initialize discovery service directly
        from .discovery.base_google_discovery import BaseGoogleDiscoveryHandler
        self.discovery = BaseGoogleDiscoveryHandler(creds, 'gmail')

        # Validación mínima de params
        to      = params.get("to")      or params.get("email")
        subject = params.get("subject")
        body    = params.get("body")    or params.get("message")
        
        # 🔧 DEBUG: Log received parameters to debug mapping issue
        self.logger.debug(f"📧 GMAIL HANDLER: Received params keys: {list(params.keys())}")
        self.logger.debug(f"📧 GMAIL HANDLER: Param types: {[(k, type(v).__name__) for k, v in params.items()]}")
        self.logger.debug(f"📧 GMAIL HANDLER: to='{to}', subject='{subject}', body='{body}'")
        
        if not to or not subject or not body:
            self.logger.error(f"📧 GMAIL HANDLER: Missing parameters - to: {'✓' if to else '✗'}, subject: {'✓' if subject else '✗'}, body: {'✓' if body else '✗'}")
            return {
                "status": "error",
                "output": None,
                "error":  "Missing 'to', 'subject', or 'body' in params",
                "duration_ms": int((time.time() - start) * 1000),
            }

        # Construir MIME message
        mime = MIMEText(body)
        mime["to"]      = to
        mime["from"]    = params.get("from", "me")
        mime["subject"] = subject

        # 🔧 FIX: Additional protection against UUID objects in MIME encoding
        try:
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        except Exception as mime_error:
            self.logger.error(f"📧 GMAIL HANDLER: MIME encoding failed: {mime_error}")
            self.logger.error(f"📧 GMAIL HANDLER: MIME headers: to={type(to)}, from={type(params.get('from', 'me'))}, subject={type(subject)}")
            return {
                "status": "error",
                "output": None,
                "error": f"MIME encoding failed: {str(mime_error)}",
                "duration_ms": int((time.perf_counter() - start) * 1000),
            }

        # ✅ Llamada con auto-discovery
        service = await self.discovery.get_main_service()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()

        return {
            "status":      "success",
            "output":      sent,
            "duration_ms": int((time.perf_counter() - start) * 1000),
        }
