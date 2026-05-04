"""add embedding column to portfolio

Revision ID: 5af155b7e486
Revises: af6448b31a7a
Create Date: 2026-01-29 17:35:44.643303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5af155b7e486'
down_revision: Union[str, None] = 'af6448b31a7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use JSON for PostgreSQL compatibility (maps to JSONB or JSON)
    op.add_column('portfolios', sa.Column('embedding', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolios', 'embedding')
