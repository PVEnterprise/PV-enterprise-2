"""add quotation_created_by to orders

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-05-20 03:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'q2r3s4t5u6v7'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('quotation_created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'),
                  nullable=True,
                  comment='User who generated the quotation')
    )


def downgrade() -> None:
    op.drop_column('orders', 'quotation_created_by')
