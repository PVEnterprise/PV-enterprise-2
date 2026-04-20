"""add bag fields to inventory

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-04-20 03:53:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h2i3j4k5l6m7'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('inventory', sa.Column('md_bag', sa.Integer(), nullable=True, comment='MD bag quantity'))
    op.add_column('inventory', sa.Column('nani_bag', sa.Integer(), nullable=True, comment='Nani bag quantity'))
    op.add_column('inventory', sa.Column('srinu_bag', sa.Integer(), nullable=True, comment='Srinu bag quantity'))
    op.add_column('inventory', sa.Column('praneeth_bag', sa.Integer(), nullable=True, comment='Praneeth bag quantity'))
    op.add_column('inventory', sa.Column('prasanna_bag', sa.Integer(), nullable=True, comment='Prasanna bag quantity'))


def downgrade() -> None:
    op.drop_column('inventory', 'prasanna_bag')
    op.drop_column('inventory', 'praneeth_bag')
    op.drop_column('inventory', 'srinu_bag')
    op.drop_column('inventory', 'nani_bag')
    op.drop_column('inventory', 'md_bag')
