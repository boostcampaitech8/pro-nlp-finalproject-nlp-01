"""add_notification_and_review_status

Revision ID: c1d2e3f4g5h6
Revises: b7c8d9e1f2a3
Create Date: 2026-01-31 11:20:00.000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'b7c8d9e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add REVIEW_REQUIRED to processingstatus enum
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'REVIEW_REQUIRED'")

    # 2. Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('link', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    # Enum removal is skipped for simplicity
