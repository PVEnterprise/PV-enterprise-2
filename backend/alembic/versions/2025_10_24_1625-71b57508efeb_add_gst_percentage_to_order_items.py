"""add_gst_percentage_to_order_items

Revision ID: 71b57508efeb
Revises: 808edbc49eda
Create Date: 2025-10-24 16:25:49.021220

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71b57508efeb'
down_revision = '808edbc49eda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add gst_percentage column to order_items table
    op.add_column('order_items', sa.Column('gst_percentage', sa.Numeric(precision=5, scale=2), nullable=True, server_default='18.00'))


def downgrade() -> None:
    # Remove gst_percentage column from order_items table
    op.drop_column('order_items', 'gst_percentage')
