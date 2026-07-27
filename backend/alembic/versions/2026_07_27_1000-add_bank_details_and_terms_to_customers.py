"""add bank details and terms_and_conditions to customers

Revision ID: ee6a2495a291
Revises: 5b41f80ae7df
Create Date: 2026-07-27 10:00:00.000000

Lets a customer's quotation bank details/terms be remembered instead of
always resetting to the hardcoded defaults in QuotationPDFModal.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee6a2495a291'
down_revision = '5b41f80ae7df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('bank_account_name', sa.String(length=100), nullable=True))
    op.add_column('customers', sa.Column('bank_account_number', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('bank_name', sa.String(length=100), nullable=True))
    op.add_column('customers', sa.Column('bank_ifsc', sa.String(length=20), nullable=True))
    op.add_column('customers', sa.Column('bank_branch', sa.String(length=100), nullable=True))
    op.add_column('customers', sa.Column('terms_and_conditions', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('customers', 'terms_and_conditions')
    op.drop_column('customers', 'bank_branch')
    op.drop_column('customers', 'bank_ifsc')
    op.drop_column('customers', 'bank_name')
    op.drop_column('customers', 'bank_account_number')
    op.drop_column('customers', 'bank_account_name')
