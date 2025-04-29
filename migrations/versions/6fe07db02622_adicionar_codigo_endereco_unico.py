"""adicionar_codigo_endereco_unico

Revision ID: 6fe07db02622
Revises: 8aab00ff3c20
Create Date: 2025-04-27 18:11:27.664829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fe07db02622'
down_revision: Union[str, None] = '8aab00ff3c20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionando campo código_endereco
    op.add_column('enderecos', sa.Column('codigo_endereco', sa.String(), nullable=True))
    
    # Preenchendo todos os registros existentes com um valor padrão
    # Formato: END-{id} - isso garante unicidade baseada no ID existente
    op.execute("""
        UPDATE enderecos
        SET codigo_endereco = 'END-' || id::text
        WHERE codigo_endereco IS NULL
    """)
    
    # Alterando para NOT NULL após preencher os dados
    op.alter_column('enderecos', 'codigo_endereco', nullable=False)
    
    # Adicionando constraint de unicidade
    op.create_unique_constraint('uq_enderecos_codigo_endereco', 'enderecos', ['codigo_endereco'])


def downgrade() -> None:
    """Downgrade schema."""
    # Removendo constraint e coluna
    op.drop_constraint('uq_enderecos_codigo_endereco', 'enderecos', type_='unique')
    op.drop_column('enderecos', 'codigo_endereco')
