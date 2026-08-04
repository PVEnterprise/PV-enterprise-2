"""add discount_percentage to customers

Revision ID: a3f9d7c1b842
Revises: ee6a2495a291
Create Date: 2026-07-30 10:00:00.000000

Lets a customer's quotation discount be remembered the same way bank
details/terms_and_conditions already are, instead of resetting every time.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f9d7c1b842'
down_revision = 'ee6a2495a291'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('discount_percentage', sa.Numeric(precision=5, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('customers', 'discount_percentage')
