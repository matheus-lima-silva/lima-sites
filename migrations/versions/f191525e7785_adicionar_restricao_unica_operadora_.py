"""adicionar_restricao_unica_operadora_endereco

Revision ID: f191525e7785
Revises: 6fe07db02622
Create Date: 2025-04-30 19:42:51.428123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'f191525e7785'
down_revision: Union[str, None] = '6fe07db02622'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Primeiro, remover as entradas duplicadas
    connection = op.get_bind()
    
    # Encontrar e manter apenas um registro para cada combinação duplicada
    connection.execute(
        text("""
        DELETE FROM endereco_operadora
        WHERE id IN (
            SELECT eo1.id
            FROM endereco_operadora eo1
            JOIN (
                SELECT endereco_id, operadora_id, MIN(id) as min_id
                FROM endereco_operadora
                GROUP BY endereco_id, operadora_id
                HAVING COUNT(*) > 1
            ) eo2 ON eo1.endereco_id = eo2.endereco_id AND eo1.operadora_id = eo2.operadora_id
            WHERE eo1.id != eo2.min_id
        )
        """)
    )
    
    # Adiciona restrição única para a combinação de endereco_id e operadora_id
    op.create_unique_constraint(
        'uq_endereco_operadora_endereco_id_operadora_id',
        'endereco_operadora',
        ['endereco_id', 'operadora_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove a restrição única
    op.drop_constraint(
        'uq_endereco_operadora_endereco_id_operadora_id',
        'endereco_operadora',
        type_='unique'
    )
