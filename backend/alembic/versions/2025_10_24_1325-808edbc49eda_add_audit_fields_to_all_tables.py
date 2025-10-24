"""Add audit fields to all tables

Revision ID: 808edbc49eda
Revises: 398ea24d581e
Create Date: 2025-10-24 13:25:35.543611

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '808edbc49eda'
down_revision = '398ea24d581e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # List of all tables that inherit from BaseModel
    tables = [
        'roles', 'users', 'customers', 'inventory', 'orders', 'order_items',
        'quotations', 'quotation_items', 'invoices', 'invoice_items',
        'approvals', 'audit_logs', 'notifications', 'dispatches', 'dispatch_items'
    ]
    
    # Get connection to check if columns exist
    conn = op.get_bind()
    
    for table in tables:
        # Check if created_by column exists
        result = conn.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='{table}' AND column_name='created_by'
        """))
        
        if not result.fetchone():
            # Add created_by column
            op.add_column(table, sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
            op.create_index(f'ix_{table}_created_by', table, ['created_by'], unique=False)
            op.create_foreign_key(f'fk_{table}_created_by', table, 'users', ['created_by'], ['id'])
        
        # Check if updated_by column exists
        result = conn.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='{table}' AND column_name='updated_by'
        """))
        
        if not result.fetchone():
            # Add updated_by column
            op.add_column(table, sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
            op.create_index(f'ix_{table}_updated_by', table, ['updated_by'], unique=False)
            op.create_foreign_key(f'fk_{table}_updated_by', table, 'users', ['updated_by'], ['id'])


def downgrade() -> None:
    # List of all tables
    tables = [
        'roles', 'users', 'customers', 'inventory', 'orders', 'order_items',
        'quotations', 'quotation_items', 'invoices', 'invoice_items',
        'approvals', 'audit_logs', 'notifications', 'dispatches', 'dispatch_items'
    ]
    
    for table in tables:
        # Drop foreign keys and indexes
        op.drop_constraint(f'fk_{table}_updated_by', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_updated_by', table_name=table)
        op.drop_column(table, 'updated_by')
        
        op.drop_constraint(f'fk_{table}_created_by', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_created_by', table_name=table)
        op.drop_column(table, 'created_by')
