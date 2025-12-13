"""add demo_items table

Revision ID: e9f0g1h2i3j4
Revises: d8e9f0g1h2i3
Create Date: 2025-12-13 23:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e9f0g1h2i3j4'
down_revision = 'd8e9f0g1h2i3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'demo_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('demo_request_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('demo_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('inventory_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory.id'), nullable=False, index=True),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.CheckConstraint('quantity > 0', name='check_demo_item_quantity_positive'),
    )


def downgrade() -> None:
    op.drop_table('demo_items')
