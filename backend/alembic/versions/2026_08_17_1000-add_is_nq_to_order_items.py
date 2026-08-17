"""add is_nq flag to order_items

Revision ID: e7f4a5b1c286
Revises: d6e3f49b0c75
Create Date: 2026-08-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e7f4a5b1c286'
down_revision = 'd6e3f49b0c75'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'order_items',
        sa.Column('is_nq', sa.Boolean(), nullable=False, server_default=sa.false(),
                  comment='Not Quoted: a dummy quotation line for a requirement we do not supply, with no inventory link and no price impact')
    )


def downgrade() -> None:
    op.drop_column('order_items', 'is_nq')
