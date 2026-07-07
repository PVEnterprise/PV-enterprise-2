"""add quotation_date column to orders

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-07-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'u6v7w8x9y0z1'
down_revision = 't5u6v7w8x9y0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('quotation_date', sa.Date(), nullable=True,
                  comment='Date shown on the quotation document; defaults to order creation date until explicitly changed')
    )
    # Backfill existing orders so the column reflects order creation date by default
    op.execute("UPDATE orders SET quotation_date = created_at::date WHERE quotation_date IS NULL")


def downgrade() -> None:
    op.drop_column('orders', 'quotation_date')
