"""adicionar_indoor_ao_tipoendereco

Revision ID: 4ca757d1ca5d
Revises: e717d3114b03
Create Date: 2025-05-02 00:53:53.939715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ca757d1ca5d'
down_revision: Union[str, None] = 'e717d3114b03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Usando SQL nativo para atualizar o tipo enum
    op.execute("ALTER TYPE tipoendereco ADD VALUE 'indoor'")


def downgrade() -> None:
    """Downgrade schema."""
    # Não é possível remover valores de um tipo enum do PostgreSQL,
    # então não podemos fazer o downgrade direto
    pass
