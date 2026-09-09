"""add status to location_checkins

Revision ID: 30db966722bc
Revises: 65fbe628f0b7
Create Date: 2026-09-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '30db966722bc'
down_revision = '65fbe628f0b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'location_checkins',
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
    )
    op.create_index('ix_location_checkins_status', 'location_checkins', ['status'])


def downgrade() -> None:
    op.drop_index('ix_location_checkins_status', table_name='location_checkins')
    op.drop_column('location_checkins', 'status')
