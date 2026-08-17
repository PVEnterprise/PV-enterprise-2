"""sync territory permissions into roles.permissions

The frontend reads role.permissions (a JSONB snapshot on the roles table)
for route/button gating, separate from the ROLE_PERMISSIONS dict in
app/core/permissions.py that gates the API. Adding a new Permission there
does not retroactively update existing role rows, so do it here.

Revision ID: a7c4e9b3f206
Revises: f3a9c7d2e158
Create Date: 2026-08-17 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7c4e9b3f206'
down_revision = 'f3a9c7d2e158'
branch_labels = None
depends_on = None


EXECUTIVE_PERMS = '{"territory:create": true, "territory:read": true, "territory:update": true, "territory:delete": true}'
READ_ONLY_PERMS = '{"territory:read": true}'


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE roles SET permissions = permissions || CAST(:perms AS jsonb) WHERE name = 'executive'"),
        {"perms": EXECUTIVE_PERMS},
    )
    conn.execute(
        sa.text("UPDATE roles SET permissions = permissions || CAST(:perms AS jsonb) WHERE name IN ('sales_rep', 'quoter')"),
        {"perms": READ_ONLY_PERMS},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE roles SET permissions = permissions - 'territory:create' - 'territory:read' "
        "- 'territory:update' - 'territory:delete' WHERE name = 'executive'"
    ))
    conn.execute(sa.text(
        "UPDATE roles SET permissions = permissions - 'territory:read' WHERE name IN ('sales_rep', 'quoter')"
    ))
