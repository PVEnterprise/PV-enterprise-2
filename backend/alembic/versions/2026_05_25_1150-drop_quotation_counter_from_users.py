"""drop quotation_counter from users, use global order MAX instead

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-05-25 11:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 's4t5u6v7w8x9'
down_revision = 'r3s4t5u6v7w8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('users', 'quotation_counter')


def downgrade() -> None:
    op.add_column(
        'users',
        sa.Column('quotation_counter', sa.Integer(), nullable=False,
                  server_default='0',
                  comment='Auto-incrementing quotation number counter per user')
    )
