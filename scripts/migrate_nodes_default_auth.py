#!/usr/bin/env python3
"""
Migration script: nodes.default_auth -> auth_policies
Migra datos existentes de default_auth a la nueva arquitectura DB
"""
import asyncio
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NodesAuthMigrator:
    """
    Migra nodes.default_auth a auth_policies y action_auth_scopes
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
    async def run_migration(self):
        """
        Ejecuta migración completa:
        1. Lee nodes.default_auth existentes
        2. Crea auth_policies correspondientes
        3. Vincula actions con policies en action_auth_scopes
        """
        logger.info("🚀 Starting migration: nodes.default_auth -> auth_policies")
        
        try:
            # 1. Obtener nodes con default_auth
            nodes_with_auth = await self._get_nodes_with_default_auth()
            logger.info(f"Found {len(nodes_with_auth)} nodes with default_auth")
            
            # 2. Crear auth_policies únicas
            auth_policies_created = await self._create_auth_policies(nodes_with_auth)
            logger.info(f"Created {len(auth_policies_created)} auth policies")
            
            # 3. Vincular actions con policies
            action_links_created = await self._create_action_auth_links(nodes_with_auth, auth_policies_created)
            logger.info(f"Created {action_links_created} action-auth links")
            
            # 4. Commit changes
            await self.db_session.commit()
            logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise
    
    async def _get_nodes_with_default_auth(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los nodes que tienen default_auth configurado
        """
        query = text("""
            SELECT 
                n.node_id,
                n.name,
                n.default_auth,
                n.use_case,
                array_agg(
                    json_build_object(
                        'action_id', a.action_id,
                        'name', a.name,
                        'description', a.description
                    )
                ) as actions
            FROM nodes n
            LEFT JOIN actions a ON a.node_id = n.node_id
            WHERE n.default_auth IS NOT NULL 
            AND n.default_auth != ''
            GROUP BY n.node_id, n.name, n.default_auth, n.use_case
            ORDER BY n.name
        """)
        
        result = await self.db_session.execute(query)
        rows = result.fetchall()
        
        nodes = []
        for row in rows:
            nodes.append({
                'node_id': row.node_id,
                'name': row.name,
                'default_auth': row.default_auth,
                'use_case': row.use_case,
                'actions': row.actions
            })
        
        return nodes
    
    async def _create_auth_policies(self, nodes_with_auth: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Crea auth_policies únicas basadas en default_auth strings
        Returns: Dict mapping auth_string -> policy_id
        """
        unique_auth_strings = set()
        for node in nodes_with_auth:
            if node['default_auth']:
                unique_auth_strings.add(node['default_auth'])
        
        auth_policies_created = {}
        
        for auth_string in unique_auth_strings:
            policy_data = self._parse_auth_string(auth_string)
            
            # Verificar si ya existe
            existing_query = text("""
                SELECT id FROM auth_policies 
                WHERE provider = :provider 
                AND service = :service 
                AND mechanism = :mechanism
            """)
            
            result = await self.db_session.execute(existing_query, {
                'provider': policy_data['provider'],
                'service': policy_data['service'],
                'mechanism': policy_data['mechanism']
            })
            
            existing = result.fetchone()
            if existing:
                auth_policies_created[auth_string] = existing.id
                logger.info(f"Found existing policy for {auth_string}: ID {existing.id}")
                continue
            
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
            
            auth_policies_created[auth_string] = policy_id
            logger.info(f"Created policy for {auth_string}: ID {policy_id}")
        
        return auth_policies_created
    
    async def _create_action_auth_links(
        self, 
        nodes_with_auth: List[Dict[str, Any]], 
        auth_policies: Dict[str, int]
    ) -> int:
        """
        Crea vínculos en action_auth_scopes para cada action
        """
        links_created = 0
        
        for node in nodes_with_auth:
            default_auth = node['default_auth']
            policy_id = auth_policies.get(default_auth)
            
            if not policy_id:
                logger.warning(f"No policy found for {default_auth}")
                continue
            
            actions = node.get('actions', [])
            if not actions or actions == [None]:
                logger.warning(f"No actions found for node {node['name']}")
                continue
            
            for action in actions:
                if not action or not action.get('action_id'):
                    continue
                
                action_id = action['action_id']
                
                # Verificar si ya existe el vínculo
                existing_query = text("""
                    SELECT id FROM action_auth_scopes 
                    WHERE action_id = :action_id AND auth_policy_id = :policy_id
                """)
                
                result = await self.db_session.execute(existing_query, {
                    'action_id': action_id,
                    'policy_id': policy_id
                })
                
                if result.fetchone():
                    logger.debug(f"Link already exists for action {action_id}")
                    continue
                
                # Crear vínculo
                insert_query = text("""
                    INSERT INTO action_auth_scopes (
                        action_id, auth_policy_id, required_scopes, 
                        priority, is_required, created_at, updated_at
                    ) VALUES (
                        :action_id, :policy_id, :required_scopes,
                        1, true, NOW(), NOW()
                    )
                """)
                
                # Determinar scopes requeridos basado en el auth_string
                required_scopes = self._get_required_scopes_for_auth(default_auth)
                
                await self.db_session.execute(insert_query, {
                    'action_id': action_id,
                    'policy_id': policy_id,
                    'required_scopes': required_scopes
                })
                
                links_created += 1
                logger.debug(f"Created link: action {action_id} -> policy {policy_id}")
        
        return links_created
    
    def _parse_auth_string(self, auth_string: str) -> Dict[str, Any]:
        """
        Parse auth_string y genera datos para auth_policy
        oauth2_google_gmail -> provider=google, service=gmail, mechanism=oauth2
        """
        try:
            # Usar oauth_utils si está disponible
            from app.utils.oauth_utils import parse_auth
            mechanism, provider, service = parse_auth(auth_string)
        except:
            # Fallback parsing
            parts = auth_string.lower().split('_', 2)
            if len(parts) >= 3:
                mechanism, provider, service = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                mechanism, provider, service = parts[0], parts[1], None
            else:
                mechanism, provider, service = 'unknown', parts[0] if parts else 'unknown', None
        
        # Mapeo de URLs base conocidas
        base_url_map = {
            'google': 'https://accounts.google.com/o/oauth2/v2/auth',
            'microsoft': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
            'dropbox': 'https://www.dropbox.com/oauth2/authorize',
            'github': 'https://github.com/login/oauth/authorize'
        }
        
        base_auth_url = base_url_map.get(provider, f'https://{provider}.com/oauth/authorize')
        
        # Mapeo de scopes máximos por provider/service
        max_scopes = self._get_max_scopes(provider, service)
        
        return {
            'provider': provider or 'unknown',
            'service': service,
            'mechanism': mechanism or 'oauth2',
            'base_auth_url': base_auth_url,
            'max_scopes': max_scopes,
            'display_name': self._generate_display_name(provider, service),
            'description': f'Auto-migrated from nodes.default_auth: {auth_string}'
        }
    
    def _get_max_scopes(self, provider: str, service: str) -> List[str]:
        """
        Determina scopes máximos basado en provider/service
        """
        scope_map = {
            'google': {
                'gmail': ['https://www.googleapis.com/auth/gmail.send'],
                'sheets': ['https://www.googleapis.com/auth/spreadsheets'],
                'calendar': ['https://www.googleapis.com/auth/calendar.events'],
                'drive': ['https://www.googleapis.com/auth/drive'],
                None: [
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.events',
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            },
            'microsoft': {
                'outlook': ['https://graph.microsoft.com/Mail.Send'],
                'teams': ['https://graph.microsoft.com/Chat.ReadWrite'],
                None: ['https://graph.microsoft.com/User.Read']
            },
            'dropbox': {
                None: ['files.content.write', 'files.content.read']
            }
        }
        
        provider_scopes = scope_map.get(provider, {})
        return provider_scopes.get(service, provider_scopes.get(None, []))
    
    def _get_required_scopes_for_auth(self, auth_string: str) -> List[str]:
        """
        Determina scopes requeridos específicos para una acción
        Por defecto usa todos los scopes disponibles del provider/service
        """
        try:
            from app.utils.oauth_utils import parse_auth
            mechanism, provider, service = parse_auth(auth_string)
        except:
            parts = auth_string.lower().split('_', 2)
            mechanism = parts[0] if parts else 'oauth2'
            provider = parts[1] if len(parts) > 1 else 'unknown'
            service = parts[2] if len(parts) > 2 else None
        
        return self._get_max_scopes(provider, service)
    
    def _generate_display_name(self, provider: str, service: str) -> str:
        """
        Genera nombre legible para la policy
        """
        if service:
            return f"{provider.title()} {service.title()}"
        else:
            return f"{provider.title()}"


async def main():
    """
    Entry point para ejecutar la migración
    """
    try:
        # Importar dependencias
        from app.db.database import get_db
        
        # Obtener sesión de BD
        db_gen = get_db()
        db_session = next(db_gen)
        
        # Ejecutar migración
        migrator = NodesAuthMigrator(db_session)
        await migrator.run_migration()
        
        logger.info("🎉 Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        raise
    finally:
        if 'db_session' in locals():
            await db_session.close()


if __name__ == "__main__":
    asyncio.run(main())