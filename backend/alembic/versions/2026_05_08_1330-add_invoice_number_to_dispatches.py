"""add invoice_number to dispatches

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-05-08 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'l6m7n8o9p0q1'
down_revision = 'k5l6m7n8o9p0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dispatches',
        sa.Column('invoice_number', sa.String(100), nullable=True, comment='Invoice number shown on the invoice PDF')
    )


def downgrade() -> None:
    op.drop_column('dispatches', 'invoice_number')
