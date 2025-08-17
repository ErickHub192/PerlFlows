# alembic/env.py

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ——————————————————————————————————————————
# 1) Configuración de logging desde alembic.ini
# ——————————————————————————————————————————
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ——————————————————————————————————————————
# 2) Carga de .env y URL de la base de datos
# ——————————————————————————————————————————
from dotenv import load_dotenv
load_dotenv()

# Usa la variable DATABASE_URL de tu .env
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL no está definido en .env")

config.set_main_option("sqlalchemy.url", database_url)

# ——————————————————————————————————————————
# 3) Importa tu metadata
# ——————————————————————————————————————————
from app.db.database import Base
import app.db.models  # importa todos tus modelos para poblar Base.metadata

target_metadata = Base.metadata

# ——————————————————————————————————————————
# 4) Funciones de migración offline / online
# ——————————————————————————————————————————
def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline' (genera SQL sin conectar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online' (conecta a la BD)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # detecta cambios de tipo de columna
            render_as_batch=True, 
            
            transactional_ddl=False,
        )
        with context.begin_transaction():
            context.run_migrations()


# ——————————————————————————————————————————
# 5) Selector de modo
# ——————————————————————————————————————————
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
