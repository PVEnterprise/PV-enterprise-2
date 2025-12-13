"""make hospital and city optional in demo_requests

Revision ID: d8e9f0g1h2i3
Revises: c7d8e9f0g1h2
Create Date: 2025-12-13 22:51:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd8e9f0g1h2i3'
down_revision = 'c7d8e9f0g1h2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make hospital_id and city nullable
    op.alter_column('demo_requests', 'hospital_id',
                    existing_type=sa.UUID(),
                    nullable=True)
    op.alter_column('demo_requests', 'city',
                    existing_type=sa.String(255),
                    nullable=True)


def downgrade() -> None:
    # Make hospital_id and city non-nullable again
    op.alter_column('demo_requests', 'city',
                    existing_type=sa.String(255),
                    nullable=False)
    op.alter_column('demo_requests', 'hospital_id',
                    existing_type=sa.UUID(),
                    nullable=False)
