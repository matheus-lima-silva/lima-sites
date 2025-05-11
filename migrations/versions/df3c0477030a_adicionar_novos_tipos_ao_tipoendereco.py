"""adicionar_novos_tipos_ao_tipoendereco

Revision ID: df3c0477030a
Revises: 4ca757d1ca5d
Create Date: 2025-05-02 01:03:54.337979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df3c0477030a'
down_revision: Union[str, None] = '4ca757d1ca5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Usando SQL nativo para atualizar o tipo enum
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'cow'")
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'fastsite'")
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'outdoor'")
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'harmonizada'")
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'ran sharing'")
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'street level'")
    op.execute("ALTER TYPE tipoendereco ADD VALUE IF NOT EXISTS 'small cell'")
    
    # Alterando a restrição do campo tipo para permitir valores nulos
    op.alter_column('enderecos', 'tipo', existing_type=sa.Enum('greenfield', 'rooftop', 'shopping', 'indoor', 
                                                               'cow', 'fastsite', 'outdoor', 'harmonizada',
                                                               'ran sharing', 'street level', 'small cell',
                                                               name='tipoendereco'), 
                   nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Não é possível remover valores de um tipo enum do PostgreSQL,
    # então não podemos fazer o downgrade direto
    pass
