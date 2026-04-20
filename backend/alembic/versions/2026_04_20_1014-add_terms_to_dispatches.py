"""add terms to dispatches

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-04-20 10:14:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'i3j4k5l6m7n8'
down_revision = 'h2i3j4k5l6m7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dispatches',
        sa.Column('terms', sa.String(255), nullable=True, comment='Payment/delivery terms shown on invoice')
    )


def downgrade() -> None:
    op.drop_column('dispatches', 'terms')
