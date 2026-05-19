"""add quotation_counter to users

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-05-20 03:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'r3s4t5u6v7w8'
down_revision = 'q2r3s4t5u6v7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('quotation_counter', sa.Integer(), nullable=False,
                  server_default='0',
                  comment='Auto-incrementing quotation number counter per user')
    )


def downgrade() -> None:
    op.drop_column('users', 'quotation_counter')
