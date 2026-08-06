"""add type, to_address, converted_order_id to demo_requests

Revision ID: b4c1e29f7d53
Revises: a3f9d7c1b842
Create Date: 2026-08-06 10:00:00.000000

Adds support for a Demo/Delivery distinction on demo requests: a free-text
"to_address" used as the challan SHIP TO block when no hospital is selected,
a "type" column distinguishing Demo from Delivery, and a "converted_order_id"
link recording the Order created when a Delivery is converted.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b4c1e29f7d53'
down_revision = 'a3f9d7c1b842'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('demo_requests', sa.Column('to_address', sa.Text(), nullable=True))
    op.add_column('demo_requests', sa.Column('type', sa.String(length=20), nullable=False, server_default='demo'))
    op.add_column('demo_requests', sa.Column('converted_order_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_demo_requests_converted_order_id_orders',
        'demo_requests', 'orders',
        ['converted_order_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_demo_requests_converted_order_id_orders', 'demo_requests', type_='foreignkey')
    op.drop_column('demo_requests', 'converted_order_id')
    op.drop_column('demo_requests', 'type')
    op.drop_column('demo_requests', 'to_address')
