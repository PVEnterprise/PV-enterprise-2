"""add quotation_number to orders

Revision ID: p1q2r3s4t5u6
Revises: o9p0q1r2s3t4
Create Date: 2026-05-20 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'p1q2r3s4t5u6'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('quotation_number', sa.Integer(), nullable=True,
                  comment='Auto-incremented quotation number per sales rep')
    )


def downgrade() -> None:
    op.drop_column('orders', 'quotation_number')
