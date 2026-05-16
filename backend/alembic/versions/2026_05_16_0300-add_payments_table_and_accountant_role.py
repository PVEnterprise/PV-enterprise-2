"""Add payments table and accountant role

Revision ID: c4f1a2b3d5e6
Revises: add_subject_to_orders
Create Date: 2026-05-16 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'c4f1a2b3d5e6'
down_revision = 'o9p0q1r2s3t4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_customer_id'), 'payments', ['customer_id'], unique=False)
    op.create_index(op.f('ix_payments_order_id'), 'payments', ['order_id'], unique=False)
    op.create_index(op.f('ix_payments_recorded_by'), 'payments', ['recorded_by'], unique=False)

    # Update executive role to include payment permissions
    op.execute(
        sa.text(
            "UPDATE roles SET permissions = permissions || "
            "'{\"payment:create\": true, \"payment:read\": true, \"payment:update\": true, \"payment:delete\": true}'::jsonb "
            "WHERE name = 'executive'"
        )
    )

    # Insert accountant role
    accountant_permissions = {
        "payment:create": True,
        "payment:read": True,
        "payment:update": True,
        "payment:delete": True,
        "customer:read": True,
        "order:read": True,
        "order:read_all": True,
        "dispatch:read": True,
    }

    op.execute(
        sa.text(
            "INSERT INTO roles (id, name, description, permissions, created_at, updated_at) "
            "VALUES (:id, :name, :description, CAST(:permissions AS jsonb), :created_at, :updated_at) "
            "ON CONFLICT (name) DO NOTHING"
        ).bindparams(
            id=str(uuid.uuid4()),
            name="accountant",
            description="Accountant — manages payment recording and tracks customer payment balances",
            permissions=str(accountant_permissions).replace("True", "true").replace("False", "false").replace("'", '"'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_recorded_by'), table_name='payments')
    op.drop_index(op.f('ix_payments_order_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_customer_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    op.execute("DELETE FROM roles WHERE name = 'accountant'")
