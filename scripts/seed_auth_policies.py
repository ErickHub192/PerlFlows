#!/usr/bin/env python3
"""
Seed script: Datos iniciales para auth_policies
Crea políticas de autenticación comunes para providers conocidos
"""
import asyncio
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthPoliciesSeeder:
    """
    Crea datos iniciales para auth_policies table
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
    async def run_seeding(self):
        """
        Ejecuta seeding completo de auth_policies
        """
        logger.info("🌱 Starting seeding: auth_policies initial data")
        
        try:
            # Obtener políticas predefinidas
            policies_to_create = self._get_predefined_policies()
            
            # Crear cada política
            created_count = 0
            for policy_data in policies_to_create:
                if await self._create_auth_policy(policy_data):
                    created_count += 1
            
            # Commit changes
            await self.db_session.commit()
            logger.info(f"✅ Seeding completed: {created_count} policies created")
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"❌ Seeding failed: {e}")
            raise
    
    def _get_predefined_policies(self) -> List[Dict[str, Any]]:
        """
        Define políticas de auth predeterminadas para providers comunes
        """
        return [
            # Google policies
            {
                'provider': 'google',
                'service': 'gmail',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'max_scopes': ['https://www.googleapis.com/auth/gmail.send'],
                'display_name': 'Google Gmail',
                'description': 'OAuth2 authentication for Google Gmail API access'
            },
            {
                'provider': 'google',
                'service': 'sheets',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'max_scopes': ['https://www.googleapis.com/auth/spreadsheets'],
                'display_name': 'Google Sheets',
                'description': 'OAuth2 authentication for Google Sheets API access'
            },
            {
                'provider': 'google',
                'service': 'calendar',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'max_scopes': ['https://www.googleapis.com/auth/calendar.events'],
                'display_name': 'Google Calendar',
                'description': 'OAuth2 authentication for Google Calendar API access'
            },
            {
                'provider': 'google',
                'service': 'drive',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'max_scopes': ['https://www.googleapis.com/auth/drive'],
                'display_name': 'Google Drive',
                'description': 'OAuth2 authentication for Google Drive API access'
            },
            {
                'provider': 'google',
                'service': None,
                'mechanism': 'oauth2',
                'base_auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'max_scopes': [
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.events',
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ],
                'display_name': 'Google',
                'description': 'OAuth2 authentication for comprehensive Google services access'
            },
            
            # Microsoft policies
            {
                'provider': 'microsoft',
                'service': 'outlook',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'max_scopes': ['https://graph.microsoft.com/Mail.Send'],
                'display_name': 'Microsoft Outlook',
                'description': 'OAuth2 authentication for Microsoft Outlook API access'
            },
            {
                'provider': 'microsoft',
                'service': 'teams',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'max_scopes': ['https://graph.microsoft.com/Chat.ReadWrite'],
                'display_name': 'Microsoft Teams',
                'description': 'OAuth2 authentication for Microsoft Teams API access'
            },
            {
                'provider': 'microsoft',
                'service': None,
                'mechanism': 'oauth2',
                'base_auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'max_scopes': [
                    'https://graph.microsoft.com/User.Read',
                    'https://graph.microsoft.com/Mail.Send',
                    'https://graph.microsoft.com/Chat.ReadWrite'
                ],
                'display_name': 'Microsoft',
                'description': 'OAuth2 authentication for Microsoft Graph API access'
            },
            
            # Dropbox policies
            {
                'provider': 'dropbox',
                'service': None,
                'mechanism': 'oauth2',
                'base_auth_url': 'https://www.dropbox.com/oauth2/authorize',
                'max_scopes': ['files.content.write', 'files.content.read'],
                'display_name': 'Dropbox',
                'description': 'OAuth2 authentication for Dropbox API access'
            },
            
            # GitHub policies
            {
                'provider': 'github',
                'service': None,
                'mechanism': 'oauth2',
                'base_auth_url': 'https://github.com/login/oauth/authorize',
                'max_scopes': ['repo', 'user:email'],
                'display_name': 'GitHub',
                'description': 'OAuth2 authentication for GitHub API access'
            },
            
            # Slack policies
            {
                'provider': 'slack',
                'service': 'slack',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://slack.com/oauth/v2/authorize',
                'max_scopes': ['chat:write', 'channels:read', 'bot'],
                'display_name': 'Slack Bot Token',
                'description': 'OAuth2 authentication for Slack Bot API access'
            },
            
            # HubSpot policies
            {
                'provider': 'hubspot',
                'service': 'hubspot',
                'mechanism': 'oauth2',
                'base_auth_url': 'https://app.hubspot.com/oauth/authorize',
                'max_scopes': ['contacts', 'content', 'timeline'],
                'display_name': 'HubSpot OAuth2',
                'description': 'OAuth2 authentication for HubSpot API access'
            },
            
            # Generic database authentication
            {
                'provider': 'database',
                'service': 'credentials',
                'mechanism': 'db',
                'base_auth_url': '',
                'max_scopes': [],
                'display_name': 'Database Credentials',
                'description': 'Database stored credentials authentication'
            },
            
            # API Key authentication
            {
                'provider': 'api_key',
                'service': None,
                'mechanism': 'api_key',
                'base_auth_url': '',
                'max_scopes': [],
                'display_name': 'API Key',
                'description': 'API Key based authentication'
            }
        ]
    
    async def _create_auth_policy(self, policy_data: Dict[str, Any]) -> bool:
        """
        Crea una auth_policy si no existe
        Returns True si se creó, False si ya existía
        """
        # Verificar si ya existe
        existing_query = text("""
            SELECT id FROM auth_policies 
            WHERE provider = :provider 
            AND COALESCE(service, '') = COALESCE(:service, '')
            AND mechanism = :mechanism
        """)
        
        result = await self.db_session.execute(existing_query, {
            'provider': policy_data['provider'],
            'service': policy_data['service'],
            'mechanism': policy_data['mechanism']
        })
        
        existing = result.fetchone()
        if existing:
            logger.debug(f"Policy already exists: {policy_data['display_name']} (ID: {existing.id})")
            return False
        
        # Crear nueva policy
        insert_query = text("""
            INSERT INTO auth_policies (
                provider, service, mechanism, base_auth_url, max_scopes,
                display_name, description, is_active, created_at, updated_at
            ) VALUES (
                :provider, :service, :mechanism, :base_auth_url, :max_scopes,
                :display_name, :description, true, NOW(), NOW()
            ) RETURNING id
        """)
        
        result = await self.db_session.execute(insert_query, policy_data)
        policy_id = result.fetchone().id
        
        logger.info(f"Created policy: {policy_data['display_name']} (ID: {policy_id})")
        return True
    
    async def verify_seeded_data(self):
        """
        Verifica que los datos se hayan creado correctamente
        """
        logger.info("🔍 Verifying seeded data...")
        
        # Contar policies creadas
        count_query = text("SELECT COUNT(*) as total FROM auth_policies")
        result = await self.db_session.execute(count_query)
        total_policies = result.fetchone().total
        
        # Obtener resumen por provider
        summary_query = text("""
            SELECT 
                provider,
                COUNT(*) as count,
                array_agg(COALESCE(service, 'default')) as services
            FROM auth_policies 
            GROUP BY provider
            ORDER BY provider
        """)
        
        result = await self.db_session.execute(summary_query)
        providers_summary = result.fetchall()
        
        logger.info(f"📊 Total auth policies: {total_policies}")
        for row in providers_summary:
            services_list = ', '.join(row.services)
            logger.info(f"  {row.provider}: {row.count} policies ({services_list})")


async def main():
    """
    Entry point para ejecutar el seeding
    """
    try:
        # Importar dependencias
        from app.db.database import get_db
        
        # Obtener sesión de BD
        db_gen = get_db()
        db_session = next(db_gen)
        
        # Ejecutar seeding
        seeder = AuthPoliciesSeeder(db_session)
        await seeder.run_seeding()
        
        # Verificar datos creados
        await seeder.verify_seeded_data()
        
        logger.info("🎉 Seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Seeding failed: {e}")
        raise
    finally:
        if 'db_session' in locals():
            await db_session.close()


if __name__ == "__main__":
    asyncio.run(main())