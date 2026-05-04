"""add view_count to recruitment

Revision ID: 29e06c94483c
Revises: 30670da7027a
Create Date: 2026-01-29 18:21:31.224805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29e06c94483c'
down_revision: Union[str, None] = '30670da7027a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recruitments', sa.Column('view_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('recruitments', 'view_count')
