"""add embedding columns to recruitment and job queries

Revision ID: 30670da7027a
Revises: 4fd0c23241d1
Create Date: 2026-01-29 18:12:36.535627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30670da7027a'
down_revision: Union[str, None] = '4fd0c23241d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recruitments', sa.Column('embedding', sa.JSON(), nullable=True))
    op.add_column('portfolio_job_queries', sa.Column('embedding', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolio_job_queries', 'embedding')
    op.drop_column('recruitments', 'embedding')
