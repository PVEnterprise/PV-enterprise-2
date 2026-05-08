"""add dc_number to dispatches

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-05-08 13:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'k5l6m7n8o9p0'
down_revision = 'j4k5l6m7n8o9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dispatches',
        sa.Column('dc_number', sa.String(100), nullable=True, comment='Delivery Challan reference number')
    )


def downgrade() -> None:
    op.drop_column('dispatches', 'dc_number')
