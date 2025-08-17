# -*- coding: utf-8 -*-
# seed_google_creation_handlers.py
"""
Script para seed de nuevos handlers de creación de Google Sheets y Docs
"""
import os
import uuid
import argparse
from dotenv import load_dotenv
from app.core.config import settings

from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    String, Enum as PgEnum, Text, Boolean, delete, insert, select, func, text
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID, ARRAY
from sqlalchemy.exc import SQLAlchemyError

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or settings.DATABASE_URL
if not DATABASE_URL:
    # URL por defecto para desarrollo
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/kyra"
    print(f"WARNING: Usando DATABASE_URL por defecto: {DATABASE_URL}")
    print("Configura DATABASE_URL en tu .env para producción")

# Conectar y definir tablas
engine = create_engine(DATABASE_URL)
metadata = MetaData()

nodes_tbl = Table(
    "nodes", metadata,
    Column("node_id", PgUUID(as_uuid=True), primary_key=True),
    Column("name", String, unique=True, nullable=False),
    Column("slug", String, nullable=False),
    Column("node_type", PgEnum("trigger","action","transform","ai","subflow", name="nodetype"), nullable=False),
    Column(
        "usage_mode",
        PgEnum("step", "tool", "step_and_tool", "function", name="nodeusagemode"),
        nullable=False,
        server_default="step",
    ),
    Column("default_auth", String, nullable=True),
    Column("use_case", Text, nullable=True),
)

actions_tbl = Table(
    "actions", metadata,
    Column("action_id", PgUUID(as_uuid=True), primary_key=True),
    Column("node_id", PgUUID(as_uuid=True), nullable=False),
    Column("name", String, nullable=False),
    Column("description", Text, nullable=True),
    Column(
        "action_type",
        PgEnum("Trigger", "Action", name="action_type"),
        nullable=False,
        server_default="Action",
    ),
    Column("auth_required", Boolean, nullable=False),
)

parameters_tbl = Table(
    "parameters", metadata,
    Column("param_id", PgUUID(as_uuid=True), primary_key=True),
    Column("action_id", PgUUID(as_uuid=True), nullable=False),
    Column("name", String, nullable=False),
    Column("description", Text, nullable=True),
    Column("required", Boolean, nullable=False, server_default=text("true")),
    Column("param_type", String, nullable=True),
)

# ================================================================
# NUEVOS NODOS DE CREACIÓN GOOGLE
# ================================================================

NEW_NODES_DATA = [
    # Google Sheets - Crear Spreadsheet
    {
        "node_id": str(uuid.uuid4()),
        "name": "Google_Sheets.create_spreadsheet",
        "slug": "google-sheets-create-spreadsheet",
        "node_type": "action",
        "usage_mode": "step_and_tool",
        "default_auth": "google",
        "use_case": "Crea nuevos Google Spreadsheets con título personalizado, configuración regional y sheets específicos. Ideal para generar reportes automáticos.",
    },
    # Google Docs - Crear Document
    {
        "node_id": str(uuid.uuid4()),
        "name": "Google_Docs.create_document",
        "slug": "google-docs-create-document",
        "node_type": "action",
        "usage_mode": "step_and_tool",
        "default_auth": "google",
        "use_case": "Crea nuevos Google Documents con título y contenido inicial estructurado. Soporte para headers, párrafos y listas.",
    },
    # Google Docs - Escribir Contenido
    {
        "node_id": str(uuid.uuid4()),
        "name": "Google_Docs.write_content",
        "slug": "google-docs-write-content",
        "node_type": "action",
        "usage_mode": "step_and_tool",
        "default_auth": "google",
        "use_case": "Escribe contenido en Google Documents existentes con formato avanzado, tablas e imágenes. Posición específica de inserción.",
    },
]

NEW_ACTIONS_DATA = [
    # Google Sheets - Create Spreadsheet
    {
        "action_id": str(uuid.uuid4()),
        "name": "create_spreadsheet",
        "description": "Crea un nuevo Google Spreadsheet con configuración personalizada y sheets específicos",
        "action_type": "Action",
        "node_name": "Google_Sheets.create_spreadsheet",
        "parameters": [
            {"name": "title", "description": "Título del nuevo spreadsheet (REQUERIDO)", "required": True, "param_type": "string"},
            {"name": "locale", "description": "Configuración regional del spreadsheet", "required": False, "param_type": "string"},
            {"name": "time_zone", "description": "Zona horaria del spreadsheet", "required": False, "param_type": "string"},
            {"name": "sheet_properties", "description": "Propiedades de sheets iniciales (JSON array)", "required": False, "param_type": "json"},
        ]
    },
    # Google Docs - Create Document
    {
        "action_id": str(uuid.uuid4()),
        "name": "create_document",
        "description": "Crea un nuevo Google Document con título y contenido inicial estructurado",
        "action_type": "Action",
        "node_name": "Google_Docs.create_document",
        "parameters": [
            {"name": "title", "description": "Título del nuevo documento (REQUERIDO)", "required": True, "param_type": "string"},
            {"name": "initial_content", "description": "Contenido inicial del documento", "required": False, "param_type": "string"},
            {"name": "content_elements", "description": "Elementos estructurados de contenido (JSON array)", "required": False, "param_type": "json"},
        ]
    },
    # Google Docs - Write Content
    {
        "action_id": str(uuid.uuid4()),
        "name": "write_content",
        "description": "Escribe contenido en un Google Document existente con formato avanzado",
        "action_type": "Action",
        "node_name": "Google_Docs.write_content",
        "parameters": [
            {"name": "document_id", "description": "ID del documento existente (REQUERIDO)", "required": True, "param_type": "string"},
            {"name": "content", "description": "Contenido a insertar en el documento", "required": False, "param_type": "string"},
            {"name": "position", "description": "Posición donde insertar (número, opcional)", "required": False, "param_type": "number"},
            {"name": "formatting", "description": "Opciones de formato (JSON object)", "required": False, "param_type": "json"},
            {"name": "content_type", "description": "Tipo de contenido: text, table, image", "required": False, "param_type": "string"},
            {"name": "table_data", "description": "Datos para tabla (si content_type=table)", "required": False, "param_type": "json"},
        ]
    },
]


def insert_google_creation_handlers():
    """Inserta los nuevos handlers de creación de Google"""
    print("INSERTANDO nuevos handlers de creación Google...")
    
    with engine.begin() as conn:
        # 1. Insertar nodes
        for node_data in NEW_NODES_DATA:
            # Verificar si ya existe
            existing = conn.execute(
                select(nodes_tbl.c.node_id).where(nodes_tbl.c.name == node_data["name"])
            ).fetchone()
            
            if existing:
                print(f"   WARNING: Node {node_data['name']} ya existe, saltando...")
                continue
            
            conn.execute(insert(nodes_tbl).values(node_data))
            print(f"   SUCCESS: Inserted node: {node_data['name']}")
        
        # 2. Insertar actions y parameters
        for action_data in NEW_ACTIONS_DATA:
            # Buscar node_id por nombre
            node_result = conn.execute(
                select(nodes_tbl.c.node_id).where(nodes_tbl.c.name == action_data["node_name"])
            ).fetchone()
            
            if not node_result:
                print(f"   ERROR: Node {action_data['node_name']} no encontrado, saltando action...")
                continue
            
            node_id = node_result[0]
            
            # Verificar si action ya existe
            existing_action = conn.execute(
                select(actions_tbl.c.action_id).where(
                    (actions_tbl.c.node_id == node_id) & 
                    (actions_tbl.c.name == action_data["name"])
                )
            ).fetchone()
            
            if existing_action:
                print(f"   WARNING: Action {action_data['name']} ya existe para {action_data['node_name']}, saltando...")
                continue
            
            # Insertar action
            action_insert_data = {
                "action_id": action_data["action_id"],
                "node_id": node_id,
                "name": action_data["name"],
                "description": action_data["description"],
                "action_type": action_data["action_type"],
                "auth_required": True  # Todos requieren Google OAuth
            }
            
            conn.execute(insert(actions_tbl).values(action_insert_data))
            print(f"   SUCCESS: Inserted action: {action_data['node_name']}.{action_data['name']}")
            
            # 3. Insertar parameters
            for param_data in action_data["parameters"]:
                param_insert_data = {
                    "param_id": str(uuid.uuid4()),
                    "action_id": action_data["action_id"],
                    "name": param_data["name"],
                    "description": param_data["description"],
                    "required": param_data["required"],
                    "param_type": param_data.get("param_type")
                }
                
                conn.execute(insert(parameters_tbl).values(param_insert_data))
                print(f"     PARAM: Added parameter: {param_data['name']}")


def main():
    parser = argparse.ArgumentParser(description="Seed handlers de creación Google Sheets y Docs")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar lo que se haría sin ejecutar")
    parser.add_argument("--db-url", help="URL de la base de datos (opcional)")
    
    args = parser.parse_args()
    
    # Sobrescribir DATABASE_URL si se proporciona
    global DATABASE_URL, engine
    if args.db_url:
        DATABASE_URL = args.db_url
        engine = create_engine(DATABASE_URL)
        print(f"Usando DATABASE_URL personalizada: {DATABASE_URL}")
    
    if args.dry_run:
        print("DRY RUN - Mostrando lo que se haría:")
        print(f"NUEVOS nodes: {len(NEW_NODES_DATA)}")
        print(f"NUEVAS actions: {len(NEW_ACTIONS_DATA)}")
        total_params = sum(len(action['parameters']) for action in NEW_ACTIONS_DATA)
        print(f"NUEVOS parameters: {total_params}")
        return
    
    try:
        insert_google_creation_handlers()
        
        print("\nCOMPLETADO! Handlers de creación Google insertados exitosamente!")
        print("RESUMEN:")
        print("   SUCCESS Google Sheets: create_spreadsheet")
        print("   SUCCESS Google Docs: create_document + write_content")
        print("   SUCCESS Todos con parámetros y auth Google")
        print("\nEJECUTANDO El LLM ahora puede crear Sheets y Docs automáticamente!")
        
    except SQLAlchemyError as e:
        print(f"ERROR Error de base de datos: {e}")
        raise
    except Exception as e:
        print(f"ERROR Error: {e}")
        raise


if __name__ == "__main__":
    main()