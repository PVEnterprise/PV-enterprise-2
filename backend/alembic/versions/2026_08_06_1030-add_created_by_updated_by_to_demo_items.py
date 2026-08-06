"""add created_by, updated_by to demo_items

Revision ID: c5d2f38a9e64
Revises: b4c1e29f7d53
Create Date: 2026-08-06 10:30:00.000000

The original demo_items table migration omitted these audit columns, unlike
every sibling item table (order_items, invoice_items, quotation_items). Since
DemoItem inherits from BaseModel, which declares created_by/updated_by, any
query selecting a DemoItem's full column set (e.g. loading a demo request's
items) fails with UndefinedColumn against a database missing them.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c5d2f38a9e64'
down_revision = 'b4c1e29f7d53'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('demo_items', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('demo_items', sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_demo_items_created_by_users', 'demo_items', 'users', ['created_by'], ['id'])
    op.create_foreign_key('fk_demo_items_updated_by_users', 'demo_items', 'users', ['updated_by'], ['id'])
    op.create_index('ix_demo_items_created_by', 'demo_items', ['created_by'])
    op.create_index('ix_demo_items_updated_by', 'demo_items', ['updated_by'])


def downgrade() -> None:
    op.drop_index('ix_demo_items_updated_by', table_name='demo_items')
    op.drop_index('ix_demo_items_created_by', table_name='demo_items')
    op.drop_constraint('fk_demo_items_updated_by_users', 'demo_items', type_='foreignkey')
    op.drop_constraint('fk_demo_items_created_by_users', 'demo_items', type_='foreignkey')
    op.drop_column('demo_items', 'updated_by')
    op.drop_column('demo_items', 'created_by')
