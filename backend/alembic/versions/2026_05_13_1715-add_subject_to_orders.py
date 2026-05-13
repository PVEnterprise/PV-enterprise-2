"""add subject column to orders

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-05-13 17:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'o9p0q1r2s3t4'
down_revision = 'n8o9p0q1r2s3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('subject', sa.String(255), nullable=True,
                  comment='Quotation subject line shown below Bill To')
    )


def downgrade() -> None:
    op.drop_column('orders', 'subject')
