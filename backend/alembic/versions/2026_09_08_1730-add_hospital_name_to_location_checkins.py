"""add hospital_name to location_checkins

Revision ID: 65fbe628f0b7
Revises: c6d6905a2efa
Create Date: 2026-09-08 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '65fbe628f0b7'
down_revision = 'c6d6905a2efa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill existing rows with '' via server_default, then drop the
    # default so future inserts must supply a real value.
    op.add_column(
        'location_checkins',
        sa.Column('hospital_name', sa.String(255), nullable=False, server_default=''),
    )
    op.alter_column('location_checkins', 'hospital_name', server_default=None)


def downgrade() -> None:
    op.drop_column('location_checkins', 'hospital_name')
