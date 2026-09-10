"""make location_checkins.recorded_at timezone-aware

Revision ID: 25ffccdc7b02
Revises: 30db966722bc
Create Date: 2026-09-10 15:00:00.000000

The column was a naive `timestamp without time zone`, so the API serialized
it with no UTC offset at all — any viewer parsed that raw wall-clock number
as if it were already their own local time instead of converting from UTC
(e.g. an IST admin viewing "10:05:00" as 10:05 AM IST when it was actually
10:05 AM UTC = 3:35 PM IST). Existing values were always written from
`new Date(...).toISOString()` on the device, i.e. genuinely UTC, so
`AT TIME ZONE 'UTC'` reinterprets them correctly without shifting anything.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '25ffccdc7b02'
down_revision = '30db966722bc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE location_checkins "
        "ALTER COLUMN recorded_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING recorded_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE location_checkins "
        "ALTER COLUMN recorded_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING recorded_at AT TIME ZONE 'UTC'"
    )
