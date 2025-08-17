"""
Google Sheets Discovery Handler
Descubre hojas de cálculo específicamente y puede leer su estructura
"""
import logging
from typing import Dict, Any, List, Optional
from googleapiclient.errors import HttpError

from .discovery_factory import register_discovery_handler
from .base_google_discovery import BaseGoogleDiscoveryHandler

logger = logging.getLogger(__name__)


@register_discovery_handler("google_sheets", "googlesheets", "sheets")
class GoogleSheetsDiscoveryHandler(BaseGoogleDiscoveryHandler):
    """
    Discovery handler específico para Google Sheets
    Puede descubrir hojas y leer su estructura (nombres de hojas, rangos, etc.)
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials, service_name='sheets')
    
    async def discover_files(
        self, 
        file_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Descubre hojas de cálculo de Google Sheets
        """
        try:
            # ✅ Usar servicio auto-discovered
            drive_service = await self.get_drive_service()
            
            # Buscar solo spreadsheets
            query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            
            results = drive_service.files().list(
                q=query,
                pageSize=min(limit, 100),
                fields="files(id,name,mimeType,size,modifiedTime,createdTime,webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            # Formatear con información específica de Sheets
            discovered_files = []
            for file in files:
                file_info = await self._format_sheets_file(file)
                discovered_files.append(file_info)
            
            self.logger.info(f"Discovered {len(discovered_files)} Google Sheets")
            return discovered_files
            
        except HttpError as e:
            self.logger.error(f"Google Sheets discovery error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering Google Sheets: {e}")
            return []
    
    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Obtiene metadata detallada de una hoja de cálculo incluyendo estructura interna
        """
        try:
            # ✅ Usar servicio auto-discovered
            sheets_service = await self.get_main_service()
            
            # Obtener información de la hoja
            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=file_id,
                includeGridData=False
            ).execute()
            
            return await self._format_detailed_sheets_info(spreadsheet)
            
        except HttpError as e:
            self.logger.error(f"Error getting sheets metadata: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error getting sheets metadata: {e}")
            return {}
    
    async def get_sheet_data_preview(
        self, 
        file_id: str, 
        sheet_name: str = None,
        range_name: str = "A1:E10"
    ) -> Dict[str, Any]:
        """
        Obtiene preview de datos de una hoja específica
        """
        try:
            # ✅ Usar servicio auto-discovered
            sheets_service = await self.get_main_service()
            
            # Si no se especifica hoja, usar la primera
            if not sheet_name:
                spreadsheet = sheets_service.spreadsheets().get(
                    spreadsheetId=file_id,
                    fields="sheets.properties.title"
                ).execute()
                
                sheets = spreadsheet.get('sheets', [])
                if sheets:
                    sheet_name = sheets[0]['properties']['title']
                else:
                    return {"error": "No sheets found"}
            
            # Construir rango completo
            full_range = f"{sheet_name}!{range_name}"
            
            # Obtener datos
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=file_id,
                range=full_range
            ).execute()
            
            values = result.get('values', [])
            
            return {
                "sheet_name": sheet_name,
                "range": range_name,
                "data": values,
                "rows_count": len(values),
                "columns_count": max(len(row) for row in values) if values else 0,
                "has_headers": len(values) > 0
            }
            
        except HttpError as e:
            self.logger.error(f"Error getting sheet data preview: {e}")
            return {"error": str(e)}
        except Exception as e:
            self.logger.error(f"Error getting sheet data preview: {e}")
            return {"error": str(e)}
    
    async def _format_sheets_file(self, file: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatea archivo de Google Sheets con información específica
        """
        # Intentar obtener información básica de hojas
        sheet_info = {"sheets_count": "unknown", "sheet_names": []}
        
        try:
            # ✅ Usar servicio auto-discovered
            sheets_service = await self.get_main_service()
            
            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=file['id'],
                fields="sheets.properties.title"
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_info = {
                "sheets_count": len(sheets),
                "sheet_names": [sheet['properties']['title'] for sheet in sheets]
            }
            
        except Exception as e:
            self.logger.debug(f"Could not get sheet info for {file['id']}: {e}")
        
        structure = {
            "type": "spreadsheet",
            "has_sheets": True,
            "sheets_count": sheet_info["sheets_count"],
            "sheet_names": sheet_info["sheet_names"],
            "can_read_data": True,
            "supports_formulas": True
        }
        
        metadata = {
            "mime_type": file.get('mimeType'),
            "web_view_link": file.get('webViewLink'),
            "sheet_info": sheet_info,
            "provider_specific": "google_sheets"
        }
        
        return self._format_file_info(
            file_id=file['id'],
            name=file['name'],
            file_type='spreadsheet',
            structure=structure,
            icon='📊',
            metadata=metadata,
            size=file.get('size'),
            modified=file.get('modifiedTime'),
            created=file.get('createdTime'),
            mime_type=file.get('mimeType'),
            url=file.get('webViewLink')
        )
    
    async def _format_detailed_sheets_info(self, spreadsheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatea información detallada de una hoja de cálculo
        """
        properties = spreadsheet.get('properties', {})
        sheets = spreadsheet.get('sheets', [])
        
        # Analizar cada hoja
        sheets_details = []
        for sheet in sheets:
            sheet_props = sheet.get('properties', {})
            grid_props = sheet_props.get('gridProperties', {})
            
            sheet_detail = {
                "title": sheet_props.get('title'),
                "sheet_id": sheet_props.get('sheetId'),
                "index": sheet_props.get('index'),
                "sheet_type": sheet_props.get('sheetType', 'GRID'),
                "row_count": grid_props.get('rowCount'),
                "column_count": grid_props.get('columnCount'),
                "frozen_rows": grid_props.get('frozenRowCount', 0),
                "frozen_columns": grid_props.get('frozenColumnCount', 0)
            }
            sheets_details.append(sheet_detail)
        
        return {
            "id": properties.get('spreadsheetId'),
            "name": properties.get('title'),
            "type": "spreadsheet",
            "provider": "google_sheets",
            "structure": {
                "type": "spreadsheet",
                "sheets_count": len(sheets),
                "sheets": sheets_details,
                "total_cells": sum(
                    (sheet.get('properties', {}).get('gridProperties', {}).get('rowCount', 0) * 
                     sheet.get('properties', {}).get('gridProperties', {}).get('columnCount', 0))
                    for sheet in sheets
                )
            },
            "metadata": {
                "locale": properties.get('locale'),
                "time_zone": properties.get('timeZone'),
                "auto_recalc": properties.get('autoRecalc'),
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{properties.get('spreadsheetId')}"
            }
        }