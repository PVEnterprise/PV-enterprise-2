"""add attachments table

Revision ID: b1c2d3e4f5g6
Revises: a0d8a1364284
Create Date: 2025-10-25 03:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = 'a0d8a1364284'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False, index=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_extension', sa.String(10), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
    )
    
    # Create indexes for better query performance
    op.create_index('ix_attachments_entity_type_entity_id', 'attachments', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_index('ix_attachments_entity_type_entity_id', table_name='attachments')
    op.drop_table('attachments')
