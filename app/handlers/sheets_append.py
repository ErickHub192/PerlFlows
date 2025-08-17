# app/connectors/handlers/sheets_append.py

import time
from typing import Any, Dict, List
from uuid import UUID

from googleapiclient.errors import HttpError
from app.connectors.factory import register_tool, register_node
from .base_google_action_handler import BaseGoogleActionHandler

@register_node("Google_Sheets.append")
@register_tool("Google_Sheets.append")
class SheetsAppendHandler(BaseGoogleActionHandler):
    """
    Handler para la acción 'append' de Google Sheets.
    Agrega nuevas filas al final de los datos existentes en la hoja.
    
    Parámetros esperados en params:
      - spreadsheet_id     (str, requerido): ID de la hoja de cálculo.
      - sheet_name         (str, requerido): Nombre de la hoja (ej: "Sheet1").
      - values             (List[List[Any]], requerido): Matriz de valores a agregar.
      - value_input_option (str, opcional): "USER_ENTERED" o "RAW" (por defecto "USER_ENTERED").
      - insert_data_option (str, opcional): "OVERWRITE" o "INSERT_ROWS" (por defecto "INSERT_ROWS").
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds, service_name='sheets')

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.perf_counter()

        # 1) Validación básica de parámetros
        spreadsheet_id = params.get("spreadsheet_id")
        sheet_name = params.get("sheet_name", "Sheet1")
        values: List[List[Any]] = params.get("values")
        input_option = params.get("value_input_option", "USER_ENTERED")
        insert_option = params.get("insert_data_option", "INSERT_ROWS")

        if not spreadsheet_id or values is None:
            return {
                "status": "error",
                "error": "Faltan parámetros requeridos: spreadsheet_id y values",
                "duration_ms": 0
            }

        if not isinstance(values, list) or len(values) == 0:
            return {
                "status": "error",
                "error": "El parámetro 'values' debe ser una lista no vacía",
                "duration_ms": 0
            }

        # ✅ Construir cliente con auto-discovery
        service = await self.get_main_service()

        # 2) Construir el rango para append (solo el nombre de la hoja)
        append_range = f"{sheet_name}!A:Z"  # Rango amplio para que Google decida dónde agregar

        # 3) Llamada a la API: spreadsheets.values.append
        try:
            resp = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=append_range,
                valueInputOption=input_option,
                insertDataOption=insert_option,
                body={"values": values}
            ).execute()
            
            status = "success"
            output = {
                "spreadsheet_id": spreadsheet_id,
                "updated_range": resp.get("updates", {}).get("updatedRange"),
                "updated_rows": resp.get("updates", {}).get("updatedRows", 0),
                "updated_columns": resp.get("updates", {}).get("updatedColumns", 0),
                "updated_cells": resp.get("updates", {}).get("updatedCells", 0),
                "appended_rows": len(values),
                "sheet_name": sheet_name,
                "raw_response": resp
            }
            error = None

        except HttpError as e:
            # Captura errores HTTP de la API
            status = "error"
            output = None
            error = f"Error HTTP {e.resp.status}: {e._get_reason()}"
        except Exception as e:
            status = "error"
            output = None
            error = f"Error inesperado: {str(e)}"

        # 4) Medir duración
        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        return {
            "status": status,
            "output": output,
            "error": error,
            "duration_ms": duration_ms
        }
