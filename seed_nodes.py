# seed_nodes.py
import os
import uuid
import argparse
from app.core.config import settings
from app.db.models import NodeType, UsageMode


from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    String, Enum as PgEnum, Text, delete, insert, select, func
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.getenv("DATABASE_URL") or settings.DATABASE_URL
if not DATABASE_URL:
    raise RuntimeError(
        "Define DATABASE_URL en tu .env o en settings.DATABASE_URL"
    )

# 2) Conectar y definir tablas (solo columnas que vamos a tocar)
engine = create_engine(DATABASE_URL)
metadata = MetaData()

nodes_tbl = Table(
    "nodes", metadata,
    Column("node_id",   PgUUID(as_uuid=True), primary_key=True),
    Column("name",      String, unique=True, nullable=False),
    Column("slug",      String, nullable=False),
    Column("node_type", PgEnum("trigger","action","transform","ai","subflow", name="nodetype"), nullable=False),
    Column(
        "usage_mode",
        PgEnum("step", "tool", "step_and_tool", "function", name="nodeusagemode"),
        nullable=False,
        server_default="step",
    ),
    Column("default_auth", String, nullable=True),
    # NOTA: omito embedding y similarity_metric porque no los insertamos aquí
)

actions_tbl = Table(
    "actions", metadata,
    Column("action_id",  PgUUID(as_uuid=True), primary_key=True),
    Column("node_id",    PgUUID(as_uuid=True), nullable=False),
    Column("name",       String, nullable=False),
    Column("description",Text, nullable=True),
    Column(
        "action_type",
        PgEnum("Trigger", "Action", name="action_type"),
        nullable=False,
        server_default="Action",
    ),
)

# 3) Tu lista “seed” de conectores
CONNECTORS = [
    {
        "name": "Gmail",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_gmail",
        "actions": [
            {"name": "send_messages", "description": "Enviar correos mediante Gmail API", "action_type": "Action"}
        ],
    },
    {
        "name": "Outlook",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_outlook",
        "actions": [
            {"name": "send_mail", "description": "Enviar correos mediante Outlook API", "action_type": "Action"}
        ],
    },
    {
        "name": "Slack",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_slack",
        "actions": [
            {"name": "post_message", "description": "Publicar mensajes en un canal de Slack", "action_type": "Action"}
        ],
    },
    {
        "name": "Telegram",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "bot_token_telegram",
        "actions": [
            {"name": "send_message", "description": "Enviar mensaje mediante Bot API de Telegram", "action_type": "Action"}
        ],
    },
    {
        "name": "WhatsApp Business",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_whatsapp",
        "actions": [
            {"name": "send_template", "description": "Enviar plantillas de WhatsApp Business", "action_type": "Action"}
        ],
    },
    {
        "name": "Google Sheets",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_google_sheets",
        "actions": [
            {"name": "read_write", "description": "Leer y escribir en Google Sheets", "action_type": "Action"}
        ],
    },
    {
        "name": "Airtable",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "api_key_airtable",
        "actions": [
            {"name": "read_write", "description": "Leer y escribir en Airtable", "action_type": "Action"}
        ],
    },
    {
        "name": "Postgres",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "db_credentials",
        "actions": [
            {"name": "run_query", "description": "Ejecutar consulta en base de datos Postgres", "action_type": "Action"}
        ],
    },
    {
        "name": "Google Calendar",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_google_calendar",
        "actions": [
            {"name": "create_event", "description": "Crear evento en Google Calendar", "action_type": "Action"}
        ],
    },
    {
        "name": "Cron Trigger",
        "node_type": NodeType.trigger.value,
        "usage_mode": UsageMode.step.value,
        "default_auth": None,
        "actions": [
            {"name": "schedule", "description": "Programar tareas con expresión cron", "action_type": "Trigger"}
        ],
    },
    {
        "name": "Google Drive",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_google_drive",
        "actions": [
            {"name": "upload_file", "description": "Subir archivo a Google Drive", "action_type": "Action"}
        ],
    },
    {
        "name": "Dropbox",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step.value,
        "default_auth": "oauth2_dropbox",
        "actions": [
            {"name": "upload_file", "description": "Subir archivo a Dropbox", "action_type": "Action"}
        ],
    },
    {
        "name": "HubSpot",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_hubspot",
        "actions": [
            {"name": "create_contact", "description": "Crear contacto en HubSpot", "action_type": "Action"}
        ],
    },
    {
        "name": "Salesforce",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_salesforce",
        "actions": [
            {"name": "create_lead", "description": "Crear lead en Salesforce", "action_type": "Action"}
        ],
    },
    {
        "name": "Stripe",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "api_key_stripe",
        "actions": [
            {"name": "create_charge", "description": "Crear cargo en Stripe", "action_type": "Action"}
        ],
    },
    {

        "name": "GitHub",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": "oauth2_github",
        "actions": [
            {"name": "create_issue", "description": "Crear issue en GitHub", "action_type": "Action"}
        ],
    },
    
        "name": "AI Agent",
        "node_type": NodeType.ai.value,
        "usage_mode": UsageMode.step.value,
        "default_auth": "openai",
        "actions": [
            {"name": "run_agent", "description": "Ejecutar subflujo IA con OpenAI", "action_type": "Action"}
        ],
    },
    {
        "name": "HTTP Request",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step_and_tool.value,
        "default_auth": None,
        "actions": [
            {"name": "request", "description": "Realizar peticiones HTTP genéricas", "action_type": "Action"}
        ],
    },
    {
        "name": "Webhook",
        "node_type": NodeType.trigger.value,
        "usage_mode": UsageMode.step.value,
        "default_auth": None,
        "actions": [
            {"name": "on_event", "description": "Escuchar eventos entrantes vía webhook", "action_type": "Trigger"}
        ],
    },
    {
        "name": "SAT",
        "node_type": NodeType.action.value,
        "usage_mode": UsageMode.step.value,
        "default_auth": "sat",
        "actions": [
            {"name": "descarga_cfdi", "description": "Descarga masiva de CFDI", "action_type": "Action"}
        ],
    },
]

def seed(reset: bool = False):
    try:
        with engine.begin() as conn:
            if reset:
                conn.execute(delete(actions_tbl))
                conn.execute(delete(nodes_tbl))

            for spec in CONNECTORS:
                # 1) Nodo idempotente
                row = conn.execute(
                    select(nodes_tbl.c.node_id)
                    .where(nodes_tbl.c.name == spec["name"])
                ).first()
                if row:
                    node_id = row[0]
                else:
                    node_id = uuid.uuid4()
                    conn.execute(
                        insert(nodes_tbl).values(
                            node_id=node_id,
                            name=spec["name"],
                            slug=func.lower(func.regexp_replace(spec["name"], "[^a-zA-Z0-9]+", "_", "g")),
                            node_type=spec["node_type"],

                            usage_mode=spec["usage_mode"],
                            default_auth=spec["default_auth"]

                        )
                    )

                # 2) Acciones idempotentes
                for act in spec["actions"]:
                    exists = conn.execute(
                        select(actions_tbl.c.action_id)
                        .where(
                            (actions_tbl.c.node_id == node_id) &
                            (actions_tbl.c.name == act["name"])
                        )
                    ).first()
                    if not exists:
                        conn.execute(
                            insert(actions_tbl).values(
                                action_id=uuid.uuid4(),
                                node_id=node_id,
                                name=act["name"],
                                description=act["description"],
                                action_type=act["action_type"]
                            )
                        )
        print(f"✅ Sembrado de {len(CONNECTORS)} conectores completado. (reset={reset})")
    except SQLAlchemyError as e:
        print("❌ Error durante seed:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed inicial de nodos y acciones.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra las tablas antes de resembrar (solo para dev/local)."
    )
    args = parser.parse_args()
    seed(reset=args.reset)
    
