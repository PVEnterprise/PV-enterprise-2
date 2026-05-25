"""add quotation_logs table with central sequence counter

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-05-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 't5u6v7w8x9y0'
down_revision = 's4t5u6v7w8x9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the global sequence for quotation numbers
    op.execute("CREATE SEQUENCE IF NOT EXISTS quotation_number_seq START 1 INCREMENT 1")

    op.create_table(
        'quotation_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('quotation_number', sa.Integer(),
                  sa.DefaultClause(sa.text("nextval('quotation_number_seq')")),
                  nullable=False, unique=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('generated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
    )
    op.create_index('ix_quotation_logs_id', 'quotation_logs', ['id'])
    op.create_index('ix_quotation_logs_order_id', 'quotation_logs', ['order_id'])
    op.create_index('ix_quotation_logs_generated_by', 'quotation_logs', ['generated_by'])
    op.create_index('ix_quotation_logs_quotation_number', 'quotation_logs', ['quotation_number'])


def downgrade() -> None:
    op.drop_table('quotation_logs')
    op.execute("DROP SEQUENCE IF EXISTS quotation_number_seq")
