"""
Generadores de datos fake para nodos de Base de Datos
"""

import random
from typing import Dict, Any, List
from app.utils.fake_data.registry import register_fake_generator
from app.utils.template_engine import template_engine


@register_fake_generator("Postgres.run_query")
def postgres_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para queries de PostgreSQL"""
    
    query = params.get("query", "").upper().strip()
    
    if query.startswith("SELECT"):
        # Simular resultados de SELECT
        rows = []
        for _ in range(random.randint(1, 5)):
            rows.append({
                "id": template_engine.generate_fake_data_for_field("id"),
                "name": template_engine.generate_fake_data_for_field("name"),
                "email": template_engine.generate_fake_data_for_field("email"),
                "created_at": template_engine.generate_fake_data_for_field("created_at"),
                "active": template_engine.generate_fake_data_for_field("active")
            })
        
        return {
            "rows": rows,
            "row_count": len(rows),
            "columns": ["id", "name", "email", "created_at", "active"],
            "execution_time_ms": random.randint(5, 100)
        }
    
    elif query.startswith(("INSERT", "UPDATE", "DELETE")):
        # Simular operaciones de modificación
        affected_rows = random.randint(1, 10)
        return {
            "affected_rows": affected_rows,
            "success": True,
            "execution_time_ms": random.randint(10, 200),
            "last_insert_id": template_engine.generate_fake_data_for_field("id") if "INSERT" in query else None
        }
    
    else:
        # Query genérico
        return {
            "success": True,
            "message": "Query ejecutado exitosamente (fake)",
            "execution_time_ms": random.randint(5, 50)
        }


@register_fake_generator("Airtable.read_write")
def airtable_fake_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera datos fake para operaciones de Airtable"""
    
    operation = params.get("operation", "read").lower()
    
    if operation == "read":
        records = []
        for _ in range(random.randint(1, 3)):
            records.append({
                "id": f"rec{template_engine.generate_fake_data_for_field('id')}",
                "fields": {
                    "Name": template_engine.generate_fake_data_for_field("name"),
                    "Email": template_engine.generate_fake_data_for_field("email"),
                    "Status": random.choice(["Active", "Pending", "Completed"]),
                    "Created": template_engine.generate_fake_data_for_field("date")
                },
                "createdTime": template_engine.generate_fake_data_for_field("datetime")
            })
        
        return {
            "records": records,
            "total_count": len(records)
        }
    
    else:  # create, update, delete
        return {
            "id": f"rec{template_engine.generate_fake_data_for_field('id')}",
            "success": True,
            "operation": operation,
            "created_time": template_engine.generate_fake_data_for_field("datetime")
        }