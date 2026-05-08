"""add po_number to dispatches

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-05-08 13:14:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'j4k5l6m7n8o9'
down_revision = 'i3j4k5l6m7n8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dispatches',
        sa.Column('po_number', sa.String(100), nullable=True, comment='Purchase Order number from customer')
    )


def downgrade() -> None:
    op.drop_column('dispatches', 'po_number')
