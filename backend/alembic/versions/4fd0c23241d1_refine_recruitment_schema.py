"""refine recruitment schema

Revision ID: 4fd0c23241d1
Revises: 5af155b7e486
Create Date: 2026-01-29 17:52:36.693119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fd0c23241d1'
down_revision: Union[str, None] = '5af155b7e486'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Data Migration: Merge job_sector into category if category is null
    op.execute("UPDATE recruitments SET category = job_sector WHERE category IS NULL AND job_sector IS NOT NULL")
    
    # 2. Drop job_sector
    op.drop_column('recruitments', 'job_sector')
    
    # 3. Drop content
    op.drop_column('recruitments', 'content')


def downgrade() -> None:
    op.add_column('recruitments', sa.Column('job_sector', sa.String(), nullable=True))
    op.add_column('recruitments', sa.Column('content', sa.Text(), nullable=True))
