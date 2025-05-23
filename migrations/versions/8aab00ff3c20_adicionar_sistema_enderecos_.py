"""adicionar_sistema_enderecos_compartilhados

Revision ID: 8aab00ff3c20
Revises: 8bb1bf92576e
Create Date: 2025-04-26 20:34:08.760252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8aab00ff3c20'
down_revision: Union[str, None] = '8bb1bf92576e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('detentoras',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('telefone_noc', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo')
    )
    op.create_table('operadoras',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo')
    )
    op.create_table('busca_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('endpoint', sa.String(), nullable=False),
    sa.Column('parametros', sa.String(), nullable=False),
    sa.Column('tipo_busca', sa.Enum('por_id', 'por_operadora', 'por_detentora', 'por_municipio', 'por_logradouro', 'por_cep', 'por_coordenadas', name='tipobusca'), nullable=False),
    sa.Column('data_hora', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('endereco_operadora',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('endereco_id', sa.Integer(), nullable=False),
    sa.Column('operadora_id', sa.Integer(), nullable=False),
    sa.Column('codigo_operadora', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['endereco_id'], ['enderecos.id'], ),
    sa.ForeignKeyConstraint(['operadora_id'], ['operadoras.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('enderecos', sa.Column('class_infra_fisica', sa.String(), nullable=True))
    op.add_column('enderecos', sa.Column('compartilhado', sa.Boolean(), nullable=False))
    op.add_column('enderecos', sa.Column('numero_estacao_anatel', sa.String(), nullable=True))
    op.add_column('enderecos', sa.Column('detentora_id', sa.Integer(), nullable=True))
    op.drop_constraint('uq_enderecos_codigo_endereco', 'enderecos', type_='unique')
    op.create_foreign_key(None, 'enderecos', 'detentoras', ['detentora_id'], ['id'])
    op.drop_column('enderecos', 'codigo_endereco')
    op.drop_column('enderecos', 'iddetentora')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('enderecos', sa.Column('iddetentora', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('enderecos', sa.Column('codigo_endereco', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'enderecos', type_='foreignkey')
    op.create_unique_constraint('uq_enderecos_codigo_endereco', 'enderecos', ['codigo_endereco'])
    op.drop_column('enderecos', 'detentora_id')
    op.drop_column('enderecos', 'numero_estacao_anatel')
    op.drop_column('enderecos', 'compartilhado')
    op.drop_column('enderecos', 'class_infra_fisica')
    op.drop_table('endereco_operadora')
    op.drop_table('busca_logs')
    op.drop_table('operadoras')
    op.drop_table('detentoras')
    # ### end Alembic commands ###
