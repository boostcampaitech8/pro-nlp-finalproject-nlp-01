"""add title to cover letter items

Revision ID: d2e3f4g5h6i7
Revises: 16463be9b530
Create Date: 2026-02-05 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e3f4g5h6i7'
down_revision = '16463be9b530' # Assuming this is the latest based on the list
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add title column to cover_letter_items table
    op.add_column('cover_letter_items', sa.Column('title', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove title column
    op.drop_column('cover_letter_items', 'title')
