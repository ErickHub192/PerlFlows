# app/ai/handlers/google_drive_upload_file_handler.py

import time
import io
import base64
from typing import Dict, Any
from uuid import UUID
from googleapiclient.http import MediaIoBaseUpload
from .base_google_action_handler import BaseGoogleActionHandler
from app.connectors.factory import register_tool, register_node

@register_node("Google_Drive.upload_file")
@register_tool("Google_Drive.upload_file")

class GoogleDriveUploadFileHandler(BaseGoogleActionHandler):
    """
    Handler para la acción GoogleDrive.upload_file.
    Parámetros esperados en `params`:
      - file_name  (str, requerido): nombre del fichero en Drive.
      - content    (str, requerido): contenido en base64.
      - folder_id  (str, opcional): ID de carpeta destino.
      - mime_type  (str, opcional): tipo MIME, defecto 'application/octet-stream'.
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds, service_name='drive')

    async def execute(
        self,
        action_id: UUID,            # no usado aquí, pero parte de la firma común
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        # ✅ Prepara servicio con auto-discovery
        service = await self.get_main_service()

        # 2) Decodifica y empaqueta el contenido
        data_b64 = params['content']
        data_bytes = base64.b64decode(data_b64)
        fh = io.BytesIO(data_bytes)

        # 3) Configura la carga multipart
        mime = params.get('mime_type', 'application/octet-stream')
        media = MediaIoBaseUpload(fh, mimetype=mime, resumable=False)

        # 4) Construye metadata
        metadata: Dict[str, Any] = {'name': params['file_name']}
        if 'folder_id' in params and params['folder_id']:
            metadata['parents'] = [params['folder_id']]

        # 5) Ejecuta la petición
        try:
            file = (
                service.files()
                       .create(body=metadata,
                               media_body=media,
                               fields='id')
                       .execute()
            )
            status = 'success'
            output = file
            error = None
        except Exception as e:
            # Captura errores de HTTP o de la librería
            status = 'error'
            output = None
            error = str(e)

        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status":      status,
            "output":      output,
            "error":       error,
            "duration_ms": duration_ms
        }
