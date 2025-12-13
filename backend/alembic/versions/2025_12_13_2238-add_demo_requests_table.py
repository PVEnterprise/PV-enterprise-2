"""add demo_requests table

Revision ID: c7d8e9f0g1h2
Revises: b1c2d3e4f5g6
Create Date: 2025-12-13 22:38:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c7d8e9f0g1h2'
down_revision = 'b1c2d3e4f5g6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create demo_requests table
    op.create_table(
        'demo_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('city', sa.String(255), nullable=False),
        sa.Column('state', sa.String(50), nullable=False, server_default='requested', index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['hospital_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('demo_requests')
