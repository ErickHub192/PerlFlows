"""
Generadores de datos fake para nodos de manejo de archivos
"""

import random
from typing import Dict, Any
from app.utils.fake_data.registry import register_fake_generator
from app.utils.template_engine import template_engine


@register_fake_generator("Dropbox.upload_file")
def dropbox_upload_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para upload a Dropbox"""
    
    filename = params.get("filename", "documento_fake.pdf")
    
    return {
        "id": template_engine.generate_fake_data_for_field("uuid"),
        "name": filename,
        "path_lower": f"/fake_uploads/{filename.lower()}",
        "path_display": f"/Fake Uploads/{filename}",
        "size": random.randint(1024, 5*1024*1024),  # 1KB a 5MB
        "server_modified": template_engine.generate_fake_data_for_field("datetime"),
        "client_modified": template_engine.generate_fake_data_for_field("datetime"),
        "rev": f"fake_rev_{random.randint(100, 999)}",
        "content_hash": template_engine.generate_fake_data_for_field("uuid"),
        "sharing_info": {
            "read_only": False,
            "parent_shared_folder_id": None,
            "modified_by": template_engine.generate_fake_data_for_field("uuid")
        }
    }


@register_fake_generator("Google_Drive.upload_file")
def gdrive_upload_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para upload a Google Drive"""
    
    filename = params.get("filename", "documento_fake.pdf")
    
    return {
        "id": template_engine.generate_fake_data_for_field("uuid"),
        "name": filename,
        "mimeType": "application/pdf",
        "size": str(random.randint(1024, 5*1024*1024)),
        "createdTime": template_engine.generate_fake_data_for_field("datetime"),
        "modifiedTime": template_engine.generate_fake_data_for_field("datetime"),
        "webViewLink": f"https://drive.google.com/file/d/{template_engine.generate_fake_data_for_field('uuid')}/view",
        "webContentLink": f"https://drive.google.com/uc?id={template_engine.generate_fake_data_for_field('uuid')}",
        "parents": [template_engine.generate_fake_data_for_field("uuid")],
        "owners": [{
            "displayName": template_engine.generate_fake_data_for_field("name"),
            "emailAddress": template_engine.generate_fake_data_for_field("email")
        }]
    }


@register_fake_generator("Sheets.read_write")
def sheets_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para Google Sheets"""
    
    operation = params.get("operation", "read").lower()
    
    if operation == "read":
        # Simular datos de celdas
        values = []
        for row in range(random.randint(2, 6)):
            if row == 0:
                # Header row
                values.append(["ID", "Nombre", "Email", "Fecha"])
            else:
                values.append([
                    template_engine.generate_fake_data_for_field("id"),
                    template_engine.generate_fake_data_for_field("name"),
                    template_engine.generate_fake_data_for_field("email"),
                    template_engine.generate_fake_data_for_field("date")
                ])
        
        return {
            "spreadsheetId": template_engine.generate_fake_data_for_field("uuid"),
            "range": params.get("range", "A1:D10"),
            "majorDimension": "ROWS",
            "values": values
        }
    
    else:  # write
        return {
            "spreadsheetId": template_engine.generate_fake_data_for_field("uuid"),
            "updatedRange": params.get("range", "A1:D10"),
            "updatedRows": random.randint(1, 10),
            "updatedColumns": random.randint(1, 4),
            "updatedCells": random.randint(4, 40)
        }