import time
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib
import json
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.connectors.factory import register_node, execute_node
from app.core.scheduler import schedule_job, unschedule_job
from .connector_handler import ActionHandler
from .trigger_registry import register_trigger_capability

# Para importar cuando necesites usar Sheets API
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError


@register_node("Sheets_Trigger.poll_changes")
@register_trigger_capability("sheets_poll", "Sheets_Trigger.poll_changes", unschedule_method="unregister")
class SheetsPollHandler(ActionHandler):
    """
    ✅ Handler para trigger de Google Sheets con polling
    
    Funcionalidades:
    1. Monitorea cambios en una hoja de cálculo específica
    2. Detecta nuevas filas, modificaciones o eliminaciones
    3. Puede monitorear rangos específicos
    4. Ejecuta workflow cuando detecta cambios
    
    Parámetros esperados en params:
      • polling_interval: int - Intervalo en segundos (mínimo 60)
      • spreadsheet_id: str - ID de la hoja de cálculo
      • sheet_name: str - Nombre de la hoja (opcional, default primera hoja)
      • range: str - Rango a monitorear (ej: "A1:Z1000")
      • watch_type: str - "new_rows", "any_change", "specific_cells"
      • flow_id: UUID del flujo a ejecutar
      • user_id: ID del usuario
      • first_step: Dict con el primer paso del workflow
      • scheduler: AsyncIOScheduler instance
      • creds: Credenciales de Google OAuth2
      • last_snapshot: Dict - Snapshot anterior de los datos
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Validar parámetros
        polling_interval = params.get("polling_interval", 300)  # Default 5 min
        spreadsheet_id = params.get("spreadsheet_id")
        sheet_name = params.get("sheet_name", "Sheet1")
        range_spec = params.get("range", "A:Z")  # Por defecto todas las columnas
        watch_type = params.get("watch_type", "any_change")
        flow_id = params.get("flow_id")
        user_id = params.get("user_id")
        first_step = params.get("first_step")
        scheduler = params.get("scheduler")
        creds = params.get("creds", {})
        last_snapshot = params.get("last_snapshot", {})
        
        if not spreadsheet_id:
            return {
                "status": "error",
                "error": "Se requiere spreadsheet_id",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
        
        # Validación de intervalo (Google limita a 100 requests/100s)
        if polling_interval < 60:
            return {
                "status": "error",
                "error": "El intervalo mínimo de polling es 60 segundos",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }

        # Si es solo validación/preparación
        if not scheduler or not flow_id or not first_step:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "sheets_poll",
                    "trigger_args": {
                        "seconds": polling_interval,
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name,
                        "range": range_spec,
                        "watch_type": watch_type
                    }
                },
                "duration_ms": duration_ms,
            }

        # ✅ Programar job real con polling
        try:
            job_id = f"sheets_{flow_id}"
            
            # Función que ejecutará el polling
            async def check_sheets():
                try:
                    # Obtener datos actuales de la hoja
                    current_data = await self._get_sheet_data(
                        creds, spreadsheet_id, sheet_name, range_spec
                    )
                    
                    # Detectar cambios según el tipo de watch
                    changes = await self._detect_changes(
                        watch_type, last_snapshot, current_data
                    )
                    
                    if changes:
                        # Ejecutar workflow para cada cambio detectado
                        for change in changes:
                            # ✅ FIX: Ejecutar workflow completo en lugar de solo el primer nodo
                            from app.handlers.workflow_execution_helper import execute_complete_workflow, extract_trigger_metadata
                            
                            # Extraer metadatos del workflow
                            flow_id, user_id, trigger_data = extract_trigger_metadata(params)
                            
                            if flow_id and user_id:
                                # Preparar datos del trigger Sheets
                                sheets_trigger_data = {
                                    **trigger_data,
                                    "sheet_change": change,
                                    "spreadsheet_id": spreadsheet_id,
                                    "sheet_name": sheet_name,
                                    "trigger_source": "sheets"
                                }
                                
                                # Ejecutar workflow completo
                                await execute_complete_workflow(
                                    flow_id=flow_id,
                                    user_id=user_id,
                                    trigger_data=sheets_trigger_data,
                                    inputs={"sheet_change": change}
                                )
                            else:
                                # Fallback: ejecutar solo el nodo si no hay metadatos de workflow
                                await execute_node(
                                    first_step["node_name"],
                                    first_step["action_name"],
                                    {
                                        **first_step.get("params", {}),
                                        "sheet_change": change,
                                        "spreadsheet_id": spreadsheet_id,
                                        "sheet_name": sheet_name,
                                        "trigger_source": "sheets"
                                    },
                                    creds,
                                )
                        
                        # Actualizar snapshot
                        params["last_snapshot"] = current_data
                        
                except Exception as e:
                    print(f"Error en Sheets polling: {str(e)}")
            
            # Crear trigger con intervalo
            trigger_args = {
                "seconds": polling_interval,
            }
            
            # Programar job
            schedule_job(
                scheduler,
                job_id,
                func=check_sheets,
                trigger_type="interval",
                trigger_args=trigger_args,
            )
            
            duration_ms = int((time.perf_counter() - start) * 1000)
            return {
                "status": "success",
                "output": {
                    "trigger_type": "sheets_poll",
                    "job_id": job_id,
                    "scheduled": True,
                    "polling_interval": polling_interval,
                    "spreadsheet_id": spreadsheet_id,
                    "trigger_args": trigger_args,
                },
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Error programando Sheets polling: {str(e)}",
                "duration_ms": int((time.perf_counter() - start) * 1000)
            }
    
    async def _get_sheet_data(
        self, 
        creds: Dict[str, Any], 
        spreadsheet_id: str,
        sheet_name: str,
        range_spec: str
    ) -> Dict[str, Any]:
        """
        Obtiene datos actuales de la hoja usando Sheets API real
        """
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            # Construir credenciales OAuth2
            google_creds = Credentials(
                token=creds.get('access_token'),
                refresh_token=creds.get('refresh_token'),
                client_id=creds.get('client_id'),
                client_secret=creds.get('client_secret'),
                token_uri='https://oauth2.googleapis.com/token'
            )
            
            # Construir servicio Sheets
            service = build('sheets', 'v4', credentials=google_creds)
            
            # Obtener datos de la hoja
            full_range = f"{sheet_name}!{range_spec}" if sheet_name else range_spec
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=full_range,
                valueRenderOption='UNFORMATTED_VALUE',
                dateTimeRenderOption='FORMATTED_STRING'
            ).execute()
            
            values = result.get('values', [])
            
            # Calcular hash para detección de cambios
            data_hash = hashlib.md5(
                json.dumps(values, sort_keys=True).encode()
            ).hexdigest()
            
            return {
                "values": values,
                "range": result.get('range', full_range),
                "timestamp": datetime.now().isoformat(),
                "hash": data_hash,
                "row_count": len(values),
                "major_dimension": result.get('majorDimension', 'ROWS')
            }
            
        except Exception as e:
            print(f"Error accediendo Sheets API: {str(e)}")
            # Fallback a simulación en caso de error
            return {
                "values": [
                    ["Error", "Sheet", "Access"],
                    [str(e), spreadsheet_id, range_spec]
                ],
                "range": f"{sheet_name}!{range_spec}",
                "timestamp": datetime.now().isoformat(),
                "hash": hashlib.md5(f"error_{time.time()}".encode()).hexdigest(),
                "error": True
            }
    
    async def _detect_changes(
        self,
        watch_type: str,
        last_snapshot: Dict[str, Any],
        current_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        ✅ Detecta cambios según el tipo de monitoreo
        """
        changes = []
        
        if not last_snapshot:
            # Primera vez, no hay cambios que reportar
            return changes
        
        last_values = last_snapshot.get("values", [])
        current_values = current_data.get("values", [])
        
        if watch_type == "new_rows":
            # Detectar nuevas filas al final
            if len(current_values) > len(last_values):
                new_rows = current_values[len(last_values):]
                for idx, row in enumerate(new_rows):
                    changes.append({
                        "type": "new_row",
                        "row_index": len(last_values) + idx,
                        "data": row,
                        "timestamp": datetime.now().isoformat()
                    })
        
        elif watch_type == "any_change":
            # Detectar cualquier cambio comparando hashes
            if last_snapshot.get("hash") != current_data.get("hash"):
                changes.append({
                    "type": "data_changed",
                    "previous_hash": last_snapshot.get("hash"),
                    "current_hash": current_data.get("hash"),
                    "timestamp": datetime.now().isoformat()
                })
        
        elif watch_type == "specific_cells":
            # Comparar celdas específicas
            for i, row in enumerate(current_values):
                if i < len(last_values):
                    for j, cell in enumerate(row):
                        if j < len(last_values[i]) and cell != last_values[i][j]:
                            changes.append({
                                "type": "cell_changed",
                                "cell": f"{chr(65+j)}{i+1}",  # A1, B2, etc
                                "old_value": last_values[i][j],
                                "new_value": cell,
                                "timestamp": datetime.now().isoformat()
                            })
        
        return changes
    
    async def unschedule(self, scheduler: AsyncIOScheduler, job_id: str) -> Dict[str, Any]:
        """
        ✅ Cancelar job de polling
        """
        try:
            unschedule_job(scheduler, job_id)
            return {
                "status": "success",
                "message": f"Sheets polling job {job_id} cancelado exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error cancelando job {job_id}: {str(e)}"
            }


@register_node("Sheets_Trigger.form_submission")
@register_trigger_capability("sheets_form", "Sheets_Trigger.form_submission")
class SheetsFormHandler(ActionHandler):
    """
    ✅ Handler para detectar envíos de Google Forms vinculados a Sheets
    
    Monitorea específicamente nuevas respuestas de formularios
    """
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        
        # Similar a poll_changes pero optimizado para Forms
        params["watch_type"] = "new_rows"
        params["range"] = "A:Z"  # Forms añaden filas completas
        
        # Delegar al handler de polling con configuración específica
        poll_handler = SheetsPollHandler()
        return await poll_handler.execute(params)