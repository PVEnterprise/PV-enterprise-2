"""Add procurement tables

Revision ID: d7e8f9a0b1c2
Revises: c4f1a2b3d5e6
Create Date: 2026-05-16 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd7e8f9a0b1c2'
down_revision = 'c4f1a2b3d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create procurements table
    op.create_table(
        'procurements',
        sa.Column('procurement_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ordered'),
        sa.Column('supplier_name', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('procurement_number'),
    )
    op.create_index(op.f('ix_procurements_id'), 'procurements', ['id'], unique=False)
    op.create_index(op.f('ix_procurements_procurement_number'), 'procurements', ['procurement_number'], unique=True)
    op.create_index(op.f('ix_procurements_status'), 'procurements', ['status'], unique=False)

    # Create procurement_items table
    op.create_table(
        'procurement_items',
        sa.Column('procurement_id', sa.UUID(), nullable=False),
        sa.Column('inventory_id', sa.UUID(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['procurement_id'], ['procurements.id']),
        sa.ForeignKeyConstraint(['inventory_id'], ['inventory.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_procurement_items_id'), 'procurement_items', ['id'], unique=False)
    op.create_index(op.f('ix_procurement_items_procurement_id'), 'procurement_items', ['procurement_id'], unique=False)
    op.create_index(op.f('ix_procurement_items_inventory_id'), 'procurement_items', ['inventory_id'], unique=False)

    # Add procurement permissions to executive role
    op.execute(
        sa.text(
            "UPDATE roles SET permissions = permissions || "
            "'{\"procurement:create\": true, \"procurement:read\": true, \"procurement:update\": true, \"procurement:delete\": true}'::jsonb "
            "WHERE name = 'executive'"
        )
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_procurement_items_inventory_id'), table_name='procurement_items')
    op.drop_index(op.f('ix_procurement_items_procurement_id'), table_name='procurement_items')
    op.drop_index(op.f('ix_procurement_items_id'), table_name='procurement_items')
    op.drop_table('procurement_items')
    op.drop_index(op.f('ix_procurements_status'), table_name='procurements')
    op.drop_index(op.f('ix_procurements_procurement_number'), table_name='procurements')
    op.drop_index(op.f('ix_procurements_id'), table_name='procurements')
    op.drop_table('procurements')
