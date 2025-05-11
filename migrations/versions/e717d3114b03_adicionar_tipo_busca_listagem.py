"""adicionar_tipo_busca_listagem

Revision ID: e717d3114b03
Revises: f191525e7785
Create Date: 2025-04-30 20:38:39.125702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e717d3114b03'
down_revision: Union[str, None] = 'f191525e7785'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
