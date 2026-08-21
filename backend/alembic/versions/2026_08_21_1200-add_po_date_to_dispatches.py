"""add po_date to dispatches

Revision ID: b8c9d0e1f2a3
Revises: a7c4e9b3f206
Create Date: 2026-08-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8c9d0e1f2a3'
down_revision = 'a7c4e9b3f206'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dispatches',
        sa.Column('po_date', sa.Date(), nullable=True, comment='Purchase Order date from customer')
    )


def downgrade() -> None:
    op.drop_column('dispatches', 'po_date')
