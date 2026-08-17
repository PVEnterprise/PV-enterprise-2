"""add territories table and customers.territory_id

Revision ID: f3a9c7d2e158
Revises: e7f4a5b1c286
Create Date: 2026-08-17 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f3a9c7d2e158'
down_revision = 'e7f4a5b1c286'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'territories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('sales_person_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['sales_person_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
    )
    op.create_index('ix_territories_name', 'territories', ['name'], unique=True)
    op.create_index('ix_territories_sales_person_id', 'territories', ['sales_person_id'])
    op.create_index('ix_territories_created_by', 'territories', ['created_by'])
    op.create_index('ix_territories_updated_by', 'territories', ['updated_by'])

    op.add_column('customers', sa.Column('territory_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('ix_customers_territory_id', 'customers', ['territory_id'])
    op.create_foreign_key(
        'fk_customers_territory_id', 'customers', 'territories', ['territory_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_customers_territory_id', 'customers', type_='foreignkey')
    op.drop_index('ix_customers_territory_id', table_name='customers')
    op.drop_column('customers', 'territory_id')

    op.drop_index('ix_territories_updated_by', table_name='territories')
    op.drop_index('ix_territories_created_by', table_name='territories')
    op.drop_index('ix_territories_sales_person_id', table_name='territories')
    op.drop_index('ix_territories_name', table_name='territories')
    op.drop_table('territories')
