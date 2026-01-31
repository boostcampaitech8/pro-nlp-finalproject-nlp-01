"""add_processing_status_to_enum

Revision ID: b7c8d9e1f2a3
Revises: af6448b31a7a
Create Date: 2026-01-31 11:10:00.000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e1f2a3'
down_revision = 'af6448b31a7a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use autocommit to allow ALTER TYPE in PostgreSQL
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'PROCESSING'")


def downgrade() -> None:
    # PostgreSQL doesn't easily support removing enum values.
    # Usually we leave them or recreate the type, but for simplicity we skip downgrade of the value itself.
    pass
