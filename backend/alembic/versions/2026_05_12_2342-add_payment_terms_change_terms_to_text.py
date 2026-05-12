"""add payment_terms and change terms to Text on dispatches

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-05-12 23:42:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm7n8o9p0q1r2'
down_revision = 'l6m7n8o9p0q1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'dispatches', 'terms',
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=True
    )
    op.add_column(
        'dispatches',
        sa.Column('payment_terms', sa.String(50), nullable=True,
                  comment='Payment terms (e.g. Net 30, Due on Receipt)')
    )


def downgrade() -> None:
    op.drop_column('dispatches', 'payment_terms')
    op.alter_column(
        'dispatches', 'terms',
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=True
    )
