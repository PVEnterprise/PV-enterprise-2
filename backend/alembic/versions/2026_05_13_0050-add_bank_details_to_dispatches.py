"""add bank detail columns to dispatches

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-05-13 00:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'n8o9p0q1r2s3'
down_revision = 'm7n8o9p0q1r2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('dispatches', sa.Column('bank_account_name',   sa.String(100), nullable=True, comment='Bank account name for invoice'))
    op.add_column('dispatches', sa.Column('bank_account_number', sa.String(50),  nullable=True, comment='Bank account number for invoice'))
    op.add_column('dispatches', sa.Column('bank_name',           sa.String(100), nullable=True, comment='Bank name for invoice'))
    op.add_column('dispatches', sa.Column('bank_ifsc',           sa.String(20),  nullable=True, comment='Bank IFSC code for invoice'))
    op.add_column('dispatches', sa.Column('bank_branch',         sa.String(100), nullable=True, comment='Bank branch for invoice'))


def downgrade() -> None:
    op.drop_column('dispatches', 'bank_branch')
    op.drop_column('dispatches', 'bank_ifsc')
    op.drop_column('dispatches', 'bank_name')
    op.drop_column('dispatches', 'bank_account_number')
    op.drop_column('dispatches', 'bank_account_name')
