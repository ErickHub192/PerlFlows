#!/usr/bin/env python3
"""
Script para eliminar nodos experimentales específicos de la base de datos
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database URL from environment
DATABASE_URL = "postgresql+asyncpg://postgres.nlklklyrcqqdtmpcvktn:donscanor192@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# Nodos a eliminar
NODES_TO_DELETE = ["AGI_Internet_Research", "BillMetaAgent"]

async def delete_experimental_nodes():
    """Elimina los nodos experimentales especificados"""
    
    # Crear engine async
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    # Crear session factory
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        try:
            print("Buscando nodos a eliminar...")
            
            # Primero, ver qué nodos existen con esos nombres
            for node_name in NODES_TO_DELETE:
                result = await session.execute(
                    text("SELECT node_id, name FROM nodes WHERE name = :name"),
                    {"name": node_name}
                )
                node = result.fetchone()
                
                if node:
                    print(f"[OK] Encontrado: {node.name} (ID: {node.node_id})")
                else:
                    print(f"[NOT FOUND] No encontrado: {node_name}")
            
            # Confirmar antes de eliminar
            confirm = input("\nProceder con la eliminacion? (si/no): ")
            if confirm.lower() not in ['si', 's', 'yes', 'y']:
                print("[CANCELLED] Operacion cancelada")
                return
            
            print("\nEliminando nodos...")
            
            # Eliminar cada nodo
            for node_name in NODES_TO_DELETE:
                # Eliminar acciones relacionadas primero (por foreign key)
                result = await session.execute(
                    text("""
                        DELETE FROM actions 
                        WHERE node_id IN (
                            SELECT node_id FROM nodes WHERE name = :name
                        )
                    """),
                    {"name": node_name}
                )
                actions_deleted = result.rowcount
                
                # Eliminar el nodo
                result = await session.execute(
                    text("DELETE FROM nodes WHERE name = :name"),
                    {"name": node_name}
                )
                nodes_deleted = result.rowcount
                
                if nodes_deleted > 0:
                    print(f"[DELETED] Eliminado: {node_name} ({actions_deleted} acciones, {nodes_deleted} nodo)")
                else:
                    print(f"[WARNING] No se encontro: {node_name}")
            
            # Commit changes
            await session.commit()
            print("\n[SUCCESS] Eliminacion completada exitosamente!")
            
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Error durante la eliminacion: {e}")
            raise
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(delete_experimental_nodes())