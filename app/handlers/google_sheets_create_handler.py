# app/handlers/google_sheets_create_handler.py

import time
from typing import Any, Dict, Optional
from uuid import UUID

from googleapiclient.errors import HttpError
from app.connectors.factory import register_tool, register_node
from .base_google_action_handler import BaseGoogleActionHandler


@register_node("Google_Sheets.create_spreadsheet")
@register_tool("Google_Sheets.create_spreadsheet")
class SheetsCreateHandler(BaseGoogleActionHandler):
    """
    Handler para crear nuevos Google Spreadsheets.
    
    Funcionalidades:
    1. Crea nuevo spreadsheet con título personalizado
    2. Configura propiedades básicas (locale, zona horaria)
    3. Opcionalmente puede crear con sheets específicos
    4. Retorna spreadsheet ID para uso posterior
    
    Parámetros esperados en params:
      • title (str, requerido): Título del nuevo spreadsheet
      • locale (str, opcional): Configuración regional (default: "es_MX")
      • time_zone (str, opcional): Zona horaria (default: "America/Mexico_City")
      • sheet_properties (List[Dict], opcional): Propiedades de sheets iniciales
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds, service_name='sheets')

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.perf_counter()

        # Validación de parámetros
        title = params.get("title")
        if not title:
            return {
                "status": "error",
                "error": "El parámetro 'title' es requerido",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }

        # Parámetros opcionales con defaults
        locale = params.get("locale", "es_MX")
        time_zone = params.get("time_zone", "America/Mexico_City")
        sheet_properties = params.get("sheet_properties", [])

        try:
            # Construir cliente con auto-discovery
            service = await self.get_main_service()

            # Configurar propiedades del spreadsheet
            spreadsheet_body = {
                'properties': {
                    'title': title,
                    'locale': locale,
                    'timeZone': time_zone
                }
            }

            # Agregar sheets personalizados si se especifican
            if sheet_properties:
                spreadsheet_body['sheets'] = []
                for sheet_prop in sheet_properties:
                    sheet_config = {
                        'properties': {
                            'title': sheet_prop.get('title', 'Sheet1'),
                            'sheetType': sheet_prop.get('type', 'GRID'),
                            'gridProperties': {
                                'rowCount': sheet_prop.get('rows', 1000),
                                'columnCount': sheet_prop.get('columns', 26)
                            }
                        }
                    }
                    spreadsheet_body['sheets'].append(sheet_config)

            # Crear el spreadsheet
            response = service.spreadsheets().create(
                body=spreadsheet_body,
                fields='spreadsheetId,properties,sheets.properties'
            ).execute()

            # Extraer información útil
            spreadsheet_id = response.get('spreadsheetId')
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            
            sheets_info = []
            for sheet in response.get('sheets', []):
                sheet_props = sheet.get('properties', {})
                sheets_info.append({
                    'sheet_id': sheet_props.get('sheetId'),
                    'title': sheet_props.get('title'),
                    'type': sheet_props.get('sheetType'),
                    'rows': sheet_props.get('gridProperties', {}).get('rowCount'),
                    'columns': sheet_props.get('gridProperties', {}).get('columnCount')
                })

            duration_ms = int((time.perf_counter() - start_ts) * 1000)
            
            return {
                "status": "success",
                "output": {
                    "spreadsheet_id": spreadsheet_id,
                    "spreadsheet_url": spreadsheet_url,
                    "title": response.get('properties', {}).get('title'),
                    "locale": response.get('properties', {}).get('locale'),
                    "time_zone": response.get('properties', {}).get('timeZone'),
                    "sheets": sheets_info,
                    "created_at": time.time()
                },
                "duration_ms": duration_ms
            }

        except HttpError as error:
            return {
                "status": "error",
                "error": f"Google Sheets API error: {error}",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }
        except Exception as error:
            return {
                "status": "error", 
                "error": f"Error inesperado creando spreadsheet: {str(error)}",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }