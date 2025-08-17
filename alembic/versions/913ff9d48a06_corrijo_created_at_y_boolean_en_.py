"""Corrijo created_at y Boolean en Parameter

Revision ID: 913ff9d48a06
Revises: 710d17d69a75
Create Date: 2025-04-23 19:31:15.833235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '913ff9d48a06'
down_revision: Union[str, None] = '710d17d69a75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Defino el enum en SQLAlchemy
    action_type = sa.Enum('Trigger', 'Action', name='action_type')
    # 2) Lo creo en la base si aún no existe
    action_type.create(op.get_bind(), checkfirst=True)

    # 3) Ahora agrego la columna usando ese tipo
    with op.batch_alter_table('actions') as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_trigger',
                action_type,
                nullable=False,
                server_default='Action'
            )
        )
    

    # ### end Alembic commands ###


def downgrade() -> None:
    with op.batch_alter_table('actions') as batch_op:
        batch_op.drop_column('is_trigger')
    # …luego elimino el tipo si quiero dejar todo limpio:
    action_type = sa.Enum(name='action_type')
    action_type.drop(op.get_bind(), checkfirst=True)
    

    # ### end Alembic commands ###
