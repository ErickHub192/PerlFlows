# app/handlers/google_docs_create_handler.py

import time
from typing import Any, Dict, Optional, List
from uuid import UUID

from googleapiclient.errors import HttpError
from app.connectors.factory import register_tool, register_node
from .base_google_action_handler import BaseGoogleActionHandler


@register_node("Google_Docs.create_document")
@register_tool("Google_Docs.create_document")
class DocsCreateHandler(BaseGoogleActionHandler):
    """
    Handler para crear nuevos Google Documents.
    
    Funcionalidades:
    1. Crea nuevo documento con título personalizado
    2. Opcionalmente puede agregar contenido inicial
    3. Soporte para texto, párrafos, headers, listas
    4. Retorna document ID para uso posterior
    
    Parámetros esperados en params:
      • title (str, requerido): Título del nuevo documento
      • initial_content (str, opcional): Contenido inicial del documento
      • content_elements (List[Dict], opcional): Elementos estructurados de contenido
        Formato: [
          {"type": "paragraph", "text": "Mi párrafo"},
          {"type": "heading", "text": "Mi Header", "level": 1},
          {"type": "list", "items": ["Item 1", "Item 2"]}
        ]
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds, service_name='docs')

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

        # Parámetros opcionales
        initial_content = params.get("initial_content", "")
        content_elements = params.get("content_elements", [])

        try:
            # Construir cliente con auto-discovery  
            service = await self.get_main_service()

            # Crear el documento básico
            document_body = {
                'title': title
            }

            # Crear documento
            response = service.documents().create(body=document_body).execute()
            document_id = response.get('documentId')

            # Si hay contenido inicial, agregarlo
            if initial_content or content_elements:
                requests = []
                index = 1  # Comenzar después del título

                # Agregar contenido simple si se especifica
                if initial_content:
                    requests.append({
                        'insertText': {
                            'location': {'index': index},
                            'text': initial_content + '\n'
                        }
                    })
                    index += len(initial_content) + 1

                # Agregar elementos estructurados
                for element in content_elements:
                    element_type = element.get('type', 'paragraph')
                    text = element.get('text', '')
                    
                    if element_type == 'paragraph':
                        requests.append({
                            'insertText': {
                                'location': {'index': index},
                                'text': text + '\n'
                            }
                        })
                        index += len(text) + 1

                    elif element_type == 'heading':
                        level = element.get('level', 1)
                        requests.extend([
                            {
                                'insertText': {
                                    'location': {'index': index},
                                    'text': text + '\n'
                                }
                            },
                            {
                                'updateParagraphStyle': {
                                    'range': {
                                        'startIndex': index,
                                        'endIndex': index + len(text)
                                    },
                                    'paragraphStyle': {
                                        'namedStyleType': f'HEADING_{level}'
                                    },
                                    'fields': 'namedStyleType'
                                }
                            }
                        ])
                        index += len(text) + 1

                    elif element_type == 'list':
                        items = element.get('items', [])
                        for item in items:
                            list_text = f"• {item}\n"
                            requests.append({
                                'insertText': {
                                    'location': {'index': index},
                                    'text': list_text
                                }
                            })
                            index += len(list_text)

                # Ejecutar todas las requests de contenido
                if requests:
                    service.documents().batchUpdate(
                        documentId=document_id,
                        body={'requests': requests}
                    ).execute()

            # Construir URL del documento
            document_url = f"https://docs.google.com/document/d/{document_id}/edit"

            duration_ms = int((time.perf_counter() - start_ts) * 1000)
            
            return {
                "status": "success",
                "output": {
                    "document_id": document_id,
                    "document_url": document_url,
                    "title": title,
                    "has_initial_content": bool(initial_content or content_elements),
                    "content_elements_count": len(content_elements),
                    "created_at": time.time()
                },
                "duration_ms": duration_ms
            }

        except HttpError as error:
            return {
                "status": "error",
                "error": f"Google Docs API error: {error}",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }
        except Exception as error:
            return {
                "status": "error",
                "error": f"Error inesperado creando documento: {str(error)}",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }


@register_node("Google_Docs.write_content")
@register_tool("Google_Docs.write_content")
class DocsWriteHandler(BaseGoogleActionHandler):
    """
    Handler para escribir contenido en Google Documents existentes.
    
    Funcionalidades:
    1. Agrega contenido a documento existente
    2. Soporte para insertar en posición específica
    3. Formateo de texto (bold, italic, color)
    4. Inserción de tablas, imágenes, etc.
    
    Parámetros esperados en params:
      • document_id (str, requerido): ID del documento existente
      • content (str, opcional): Texto a insertar
      • position (int, opcional): Posición donde insertar (default: final)
      • formatting (Dict, opcional): Opciones de formato
      • content_type (str, opcional): "text", "table", "image"
    """

    def __init__(self, creds: Dict[str, Any]):
        super().__init__(creds, service_name='docs')

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.perf_counter()

        # Validación de parámetros
        document_id = params.get("document_id")
        if not document_id:
            return {
                "status": "error",
                "error": "El parámetro 'document_id' es requerido",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }

        content = params.get("content", "")
        position = params.get("position")  # None = final del documento
        formatting = params.get("formatting", {})
        content_type = params.get("content_type", "text")

        try:
            # Construir cliente
            service = await self.get_main_service()

            # Obtener documento para determinar posición final si no se especifica
            if position is None:
                doc = service.documents().get(documentId=document_id).execute()
                position = doc.get('body', {}).get('content', [{}])[-1].get('endIndex', 1) - 1

            requests = []

            if content_type == "text":
                # Insertar texto simple
                requests.append({
                    'insertText': {
                        'location': {'index': position},
                        'text': content
                    }
                })

                # Aplicar formato si se especifica
                if formatting:
                    text_style = {}
                    if formatting.get('bold'):
                        text_style['bold'] = True
                    if formatting.get('italic'):
                        text_style['italic'] = True
                    if formatting.get('color'):
                        text_style['foregroundColor'] = {
                            'color': {'rgbColor': formatting['color']}
                        }

                    if text_style:
                        requests.append({
                            'updateTextStyle': {
                                'range': {
                                    'startIndex': position,
                                    'endIndex': position + len(content)
                                },
                                'textStyle': text_style,
                                'fields': ','.join(text_style.keys())
                            }
                        })

            elif content_type == "table":
                # Insertar tabla (ejemplo básico)
                table_data = params.get("table_data", [])
                if table_data:
                    rows = len(table_data)
                    cols = len(table_data[0]) if table_data else 1
                    
                    requests.append({
                        'insertTable': {
                            'location': {'index': position},
                            'rows': rows,
                            'columns': cols
                        }
                    })

            # Ejecutar requests
            if requests:
                service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()

            duration_ms = int((time.perf_counter() - start_ts) * 1000)
            
            return {
                "status": "success",
                "output": {
                    "document_id": document_id,
                    "content_added": len(content),
                    "position": position,
                    "content_type": content_type,
                    "formatting_applied": bool(formatting),
                    "updated_at": time.time()
                },
                "duration_ms": duration_ms
            }

        except HttpError as error:
            return {
                "status": "error",
                "error": f"Google Docs API error: {error}",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }
        except Exception as error:
            return {
                "status": "error",
                "error": f"Error escribiendo en documento: {str(error)}",
                "duration_ms": int((time.perf_counter() - start_ts) * 1000)
            }