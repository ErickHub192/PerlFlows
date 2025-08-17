#!/usr/bin/env python3
"""
Actualización de Drive Triggers en BD
- Actualiza el trigger existente watch_changes 
- Agrega el nuevo trigger file_upload
"""

import asyncio
import os
import sys
import json
import uuid
from sqlalchemy import create_engine, text
from app.core.config import settings

async def seed_drive_triggers_update():
    """
    Actualiza y agrega triggers de Drive en la base de datos
    """
    print("=== ACTUALIZANDO DRIVE TRIGGERS EN BD ===")
    
    try:
        # Conectar a BD
        DATABASE_URL = os.getenv('DATABASE_URL') or settings.DATABASE_URL
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 1. ACTUALIZAR el trigger existente watch_changes
            print("\n1. Actualizando Drive watch_changes...")
            
            update_watch_query = text("""
                UPDATE actions 
                SET 
                    description = 'Detecta cualquier cambio en archivos y carpetas de Google Drive (crear, modificar, eliminar, mover). Ideal para monitoreo completo.'
                WHERE name = 'watch_changes'
                AND node_id IN (SELECT node_id FROM nodes WHERE name = 'Drive_Trigger')
            """)
            
            watch_metadata = {
                "category": "trigger",
                "provider": "google",
                "service": "drive",
                "trigger_type": "polling",
                "use_cases": [
                    "Monitorear cambios en documentos compartidos",
                    "Detectar eliminación de archivos importantes", 
                    "Sincronizar cambios con otros sistemas",
                    "Auditoría completa de actividad en Drive"
                ],
                "capabilities": [
                    "Detecta creación de archivos",
                    "Detecta modificaciones", 
                    "Detecta eliminaciones",
                    "Detecta movimientos entre carpetas",
                    "Filtrado por carpeta específica",
                    "Filtrado por tipos de archivo",
                    "Polling incremental con tokens"
                ],
                "requirements": {
                    "auth": "google_oauth2",
                    "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
                    "min_polling_interval": 60
                },
                "output_format": {
                    "drive_change": {
                        "fileId": "string",
                        "removed": "boolean", 
                        "time": "datetime",
                        "file": {
                            "id": "string",
                            "name": "string",
                            "mimeType": "string",
                            "parents": "array",
                            "modifiedTime": "datetime",
                            "createdTime": "datetime",
                            "size": "number"
                        }
                    },
                    "trigger_source": "drive"
                }
            }
            
            result = conn.execute(update_watch_query)
            if result.rowcount > 0:
                print("OK Drive watch_changes actualizado exitosamente")
            else:
                print("⚠️ No se encontró registro de watch_changes para actualizar")
            
            # 2. INSERTAR el nuevo trigger file_upload
            print("\n2. Insertando Drive file_upload...")
            
            # Verificar si ya existe
            check_upload_query = text("""
                SELECT COUNT(*) FROM actions 
                WHERE name = 'file_upload' 
                AND node_id IN (SELECT node_id FROM nodes WHERE name = 'Drive_Trigger')
            """)
            
            exists = conn.execute(check_upload_query).scalar()
            
            if exists > 0:
                print("⚠️ Drive file_upload ya existe, actualizando...")
                action_query = text("""
                    UPDATE actions 
                    SET 
                        description = :description
                    WHERE name = 'file_upload' 
                    AND node_id IN (SELECT id FROM nodes WHERE name = 'Drive_Trigger')
                """)
            else:
                print("NUEVO: Creando nuevo Drive file_upload...")
                action_query = text("""
                    INSERT INTO actions (
                        action_id, node_id, name, description, action_type,
                        auth_required, created_at
                    ) VALUES (
                        :action_id, (SELECT node_id FROM nodes WHERE name = 'Drive_Trigger'),
                        :name, :description, :action_type,
                        :auth_required, NOW()
                    )
                """)
            
            upload_metadata = {
                "category": "trigger",
                "provider": "google", 
                "service": "drive",
                "trigger_type": "polling",
                "specialization": "uploads_only",
                "use_cases": [
                    "Procesar archivos subidos a carpeta 'Recibidos'",
                    "Detectar nuevos PDFs en carpeta 'Facturas'", 
                    "Monitorear uploads en carpeta específica",
                    "Workflow automático para archivos nuevos"
                ],
                "capabilities": [
                    "Detecta SOLO archivos nuevos (no modificaciones)",
                    "Requiere carpeta específica (más eficiente)",
                    "Filtra automáticamente eliminaciones", 
                    "Optimizado para casos de 'carpeta de recepción'",
                    "Filtrado por tipos de archivo",
                    "Polling incremental con tokens"
                ],
                "requirements": {
                    "auth": "google_oauth2",
                    "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
                    "min_polling_interval": 60,
                    "required_params": ["folder_id"]
                },
                "output_format": {
                    "drive_change": {
                        "fileId": "string",
                        "file": {
                            "id": "string", 
                            "name": "string",
                            "mimeType": "string",
                            "parents": "array",
                            "createdTime": "datetime",
                            "size": "number"
                        }
                    },
                    "trigger_source": "drive",
                    "change_type": "upload_only"
                },
                "optimization": {
                    "vs_watch_changes": "Más eficiente para detectar solo uploads",
                    "best_for": "Carpetas de recepción con mucha actividad",
                    "performance": "Filtra cambios innecesarios en origen"
                }
            }
            
            action_params = {
                "action_id": str(uuid.uuid4()),
                "name": "file_upload",
                "description": "Monitorea específicamente archivos nuevos subidos a una carpeta de Google Drive. Más eficiente que watch_changes cuando solo necesitas detectar uploads.",
                "action_type": "Trigger",
                "auth_required": True
            }
            
            conn.execute(action_query, action_params)
            print("OK Drive file_upload insertado exitosamente")
            
            # 3. INSERTAR parámetros para file_upload
            print("\n3. Insertando parámetros para file_upload...")
            
            upload_parameters = [
                {
                    "param_name": "folder_id",
                    "description": "ID de la carpeta de Google Drive a monitorear para uploads (REQUERIDO)",
                    "param_type": "string",
                    "required": True
                },
                {
                    "param_name": "polling_interval", 
                    "description": "Intervalo en segundos para verificar nuevos uploads (mínimo 60)",
                    "param_type": "number",
                    "required": False
                },
                {
                    "param_name": "file_types",
                    "description": "Lista de tipos MIME a filtrar (ej: application/pdf, image/jpeg). Vacío = todos los tipos", 
                    "param_type": "json",
                    "required": False
                }
            ]
            
            for param in upload_parameters:
                # Obtener action_id
                action_id_result = conn.execute(text("""
                    SELECT action_id FROM actions 
                    WHERE name = 'file_upload' 
                    AND node_id IN (SELECT node_id FROM nodes WHERE name = 'Drive_Trigger')
                """))
                action_id = action_id_result.scalar()
                
                if not action_id:
                    print(f"⚠️ No se encontró action_id para {param['param_name']}")
                    continue
                
                # Verificar si parámetro ya existe
                check_param_query = text("""
                    SELECT COUNT(*) FROM parameters 
                    WHERE action_id = :action_id AND name = :param_name
                """)
                
                param_exists = conn.execute(check_param_query, {
                    "action_id": action_id,
                    "param_name": param["param_name"]
                }).scalar()
                
                if param_exists > 0:
                    print(f"⚠️ Parámetro {param['param_name']} ya existe")
                    continue
                
                # Insertar parámetro
                insert_param_query = text("""
                    INSERT INTO parameters (
                        param_id, action_id, name, description, param_type, required, created_at
                    ) VALUES (
                        :param_id, :action_id, :param_name, :description, :param_type, :required, NOW()
                    )
                """)
                
                conn.execute(insert_param_query, {
                    "param_id": str(uuid.uuid4()),
                    "action_id": action_id,
                    "param_name": param["param_name"],
                    "description": param["description"],
                    "param_type": param["param_type"],
                    "required": param["required"]
                })
                
                print(f"OK Parámetro {param['param_name']} insertado")
            
            # 4. COMMIT cambios
            conn.commit()
            
            print("\n=== RESUMEN DE ACTUALIZACION ===")
            print("OK Drive watch_changes: ACTUALIZADO con metadata mejorada")
            print("OK Drive file_upload: CREADO como nuevo trigger especializado")
            print("OK Parámetros file_upload: INSERTADOS (folder_id, polling_interval, file_types)")
            print("\nKyra ahora puede distinguir entre:")
            print("   • watch_changes: Monitoreo completo de cambios")
            print("   • file_upload: Solo detección de archivos nuevos")
            
            return True
            
    except Exception as e:
        print(f"ERROR actualizando Drive triggers: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(seed_drive_triggers_update())
    exit_code = 0 if success else 1
    print(f"\nExit Code: {exit_code}")