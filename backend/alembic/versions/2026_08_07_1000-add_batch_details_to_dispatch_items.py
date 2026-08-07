"""add batch/mfg/exp columns to dispatch_items

Revision ID: d6e3f49b0c75
Revises: c5d2f38a9e64
Create Date: 2026-08-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd6e3f49b0c75'
down_revision = 'c5d2f38a9e64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('dispatch_items', sa.Column('batch_no', sa.String(length=100), nullable=True))
    op.add_column('dispatch_items', sa.Column('mfg_date', sa.Date(), nullable=True))
    op.add_column('dispatch_items', sa.Column('exp_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('dispatch_items', 'exp_date')
    op.drop_column('dispatch_items', 'mfg_date')
    op.drop_column('dispatch_items', 'batch_no')
