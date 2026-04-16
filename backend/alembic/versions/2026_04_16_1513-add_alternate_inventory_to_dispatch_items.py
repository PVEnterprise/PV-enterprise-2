"""add alternate inventory columns to dispatch_items

Revision ID: f0a1b2c3d4e5
Revises: e9f0g1h2i3j4
Create Date: 2026-04-16 15:13:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f0a1b2c3d4e5'
down_revision = 'e9f0g1h2i3j4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dispatch_items',
        sa.Column('alternate_inventory_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'dispatch_items',
        sa.Column('alternate_quantity', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_dispatch_items_alternate_inventory',
        'dispatch_items', 'inventory',
        ['alternate_inventory_id'], ['id']
    )
    op.create_index(
        'ix_dispatch_items_alternate_inventory_id',
        'dispatch_items', ['alternate_inventory_id']
    )


def downgrade() -> None:
    op.drop_index('ix_dispatch_items_alternate_inventory_id', table_name='dispatch_items')
    op.drop_constraint('fk_dispatch_items_alternate_inventory', 'dispatch_items', type_='foreignkey')
    op.drop_column('dispatch_items', 'alternate_quantity')
    op.drop_column('dispatch_items', 'alternate_inventory_id')
