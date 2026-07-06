"""add field visit tracking: users.city, leads, field_visits, sales_attendance

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-07-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'u6v7w8x9y0z1'
down_revision = 't5u6v7w8x9y0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('city', sa.String(100), nullable=True))
    op.create_index('ix_users_city', 'users', ['city'])

    op.create_table(
        'leads',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('hospital_name', sa.String(255), nullable=True),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='active'),
        sa.Column('converted_customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
    )
    op.create_index('ix_leads_id', 'leads', ['id'])
    op.create_index('ix_leads_name', 'leads', ['name'])
    op.create_index('ix_leads_city', 'leads', ['city'])
    op.create_index('ix_leads_status', 'leads', ['status'])
    op.create_index('ix_leads_converted_customer_id', 'leads', ['converted_customer_id'])
    op.create_index('ix_leads_created_by', 'leads', ['created_by'])
    op.create_index('ix_leads_updated_by', 'leads', ['updated_by'])

    op.create_table(
        'field_visits',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('visit_date', sa.Date(), nullable=False),
        sa.Column('sales_rep_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('in_time', sa.Time(), nullable=True),
        sa.Column('out_time', sa.Time(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.CheckConstraint(
            '(customer_id IS NOT NULL AND lead_id IS NULL) OR (customer_id IS NULL AND lead_id IS NOT NULL)',
            name='check_field_visit_exactly_one_target',
        ),
    )
    op.create_index('ix_field_visits_id', 'field_visits', ['id'])
    op.create_index('ix_field_visits_visit_date', 'field_visits', ['visit_date'])
    op.create_index('ix_field_visits_sales_rep_id', 'field_visits', ['sales_rep_id'])
    op.create_index('ix_field_visits_customer_id', 'field_visits', ['customer_id'])
    op.create_index('ix_field_visits_lead_id', 'field_visits', ['lead_id'])
    op.create_index('ix_field_visits_created_by', 'field_visits', ['created_by'])
    op.create_index('ix_field_visits_updated_by', 'field_visits', ['updated_by'])
    op.create_index('ix_field_visits_rep_date', 'field_visits', ['sales_rep_id', 'visit_date'])

    op.create_table(
        'sales_attendance',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('sales_rep_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('sales_rep_id', 'attendance_date', name='uq_sales_attendance_rep_date'),
    )
    op.create_index('ix_sales_attendance_id', 'sales_attendance', ['id'])
    op.create_index('ix_sales_attendance_sales_rep_id', 'sales_attendance', ['sales_rep_id'])
    op.create_index('ix_sales_attendance_attendance_date', 'sales_attendance', ['attendance_date'])
    op.create_index('ix_sales_attendance_created_by', 'sales_attendance', ['created_by'])
    op.create_index('ix_sales_attendance_updated_by', 'sales_attendance', ['updated_by'])


def downgrade() -> None:
    op.drop_table('sales_attendance')
    op.drop_table('field_visits')
    op.drop_table('leads')
    op.drop_index('ix_users_city', table_name='users')
    op.drop_column('users', 'city')
