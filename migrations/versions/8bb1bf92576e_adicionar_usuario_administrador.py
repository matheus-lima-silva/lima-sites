"""adicionar_usuario_administrador

Revision ID: 8bb1bf92576e
Revises: faf2b0ea3941
Create Date: 2025-04-25 20:25:35.777678

"""
from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '8bb1bf92576e'
down_revision: Union[str, None] = 'faf2b0ea3941'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Verifica se já existe algum usuário com nível super_usuario
    connection = op.get_bind()
    
    # Verifica se já existe algum administrador
    result = connection.execute(text(
        "SELECT COUNT(*) FROM usuarios WHERE nivel_acesso = 'super_usuario'"
    ))
    
    count = result.scalar()
    
    # Obtém telefone e nome do administrador das variáveis de ambiente
    admin_phone = os.environ.get('ADMIN_PHONE', '+5521982427418')
    admin_name = os.environ.get('ADMIN_NAME', 'Administrador')
    
    # Se não existir nenhum administrador, cria um
    if count == 0:
        op.execute(
            text("""
                INSERT INTO usuarios (telefone, nivel_acesso, nome, created_at, last_seen)
                VALUES (:telefone, 'super_usuario', :nome, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """).bindparams(telefone=admin_phone, nome=admin_name)
        )
        print("✅ Usuário administrador padrão criado com sucesso!")
        print(f"📱 Telefone: '{admin_phone}'")
        print(f"👤 Nome: '{admin_name}'")
        print("🔑 Nível de acesso: 'super_usuario'")


def downgrade() -> None:
    """Downgrade schema."""
    # Ao fazer downgrade, não remove o usuário administrador para evitar perda de dados
    pass
