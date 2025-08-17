"""insert_use_case

Revision ID: 35731cac8b89
Revises: d3f6ce1acfb5
Create Date: 2025-04-18 15:41:18.385386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35731cac8b89'
down_revision: Union[str, None] = 'd3f6ce1acfb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
      UPDATE nodes SET use_case = CASE name
        WHEN 'Gmail'            THEN 'Enviar correos automáticos de bienvenida o confirmación cuando se registra un formulario o se crea un nuevo registro.'
        WHEN 'Outlook'          THEN 'Disparar emails de alerta desde cuentas corporativas M365 cuando el CRM detecta un nuevo lead o un ticket pasa a urgente.'
        WHEN 'Slack'            THEN 'Publicar mensajes en un canal cuando tu CRM recibe actividad nueva o cuando un flujo CI/CD falla, para que el equipo actúe al instante.'
        WHEN 'Telegram'         THEN 'Enviar notificaciones de monitoreo y alertas de seguridad a un grupo privado mediante Bot API.'
        WHEN 'WhatsApp Business'THEN 'Mandar actualizaciones de pedido y recordatorios de pago a clientes directamente en WhatsApp usando plantillas aprobadas.'
        WHEN 'Google Sheets'    THEN 'Agregar filas y generar reportes automáticos cuando un formulario o webhook recibe nuevos datos.'
        WHEN 'Airtable'         THEN 'Sincronizar bases de tareas y crear copias de seguridad al detectar cambios en registros.'
        WHEN 'Postgres'         THEN 'Ejecutar consultas programadas para alimentar dashboards o exportar datos a otros sistemas.'
        WHEN 'Google Calendar'  THEN 'Crear eventos de recordatorio o reuniones a partir de tickets o formularios confirmados.'
        WHEN 'Cron Trigger'     THEN 'Disparar flujos recurrentes (cada día, hora o minuto) usando expresiones cron estándar.'
        WHEN 'Google Drive'     THEN 'Respaldar automáticamente archivos adjuntos de correo o facturas en carpetas organizadas.'
        WHEN 'Dropbox'          THEN 'Guardar copias nocturnas de reportes o bases de datos para recuperación ante desastres.'
        WHEN 'HubSpot'          THEN 'Crear contactos o deals cuando llega un nuevo lead desde formularios o anuncios.'
        WHEN 'Salesforce'       THEN 'Registrar leads y notificar al equipo de ventas en tiempo real.'
        WHEN 'Stripe'           THEN 'Crear cargos o suscripciones y enviar recibos automáticos a clientes.'
        WHEN 'AI Agent'         THEN 'Generar resúmenes, respuestas o textos personalizados usando un modelo de lenguaje grande (OpenAI).'
        ELSE use_case
      END;
    """)



def downgrade() -> None:
    op.execute("UPDATE nodes SET use_case = NULL;")
