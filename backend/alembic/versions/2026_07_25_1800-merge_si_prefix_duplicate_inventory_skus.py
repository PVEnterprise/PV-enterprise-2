"""merge SI-prefix duplicate inventory SKUs (e.g. "137" vs "SI 137")

Revision ID: 5b41f80ae7df
Revises: a6d97996ce12
Create Date: 2026-07-25 18:00:00.000000

Another duplicate pattern: the same item entered both as a bare number
("137") and with an "SI " prefix ("SI 137"). Per the user, "SI 137" is
the correct SKU and its own unit_price is correct; the bare-number row
holds the correct stock_quantity, which gets added to (not replacing)
whatever stock the "SI " row already has, since 9 of these 567 pairs
have nonzero stock on both sides. FK references are repointed from the
bare-number row onto the "SI " row before it's deleted.
"""
from alembic import op
import sqlalchemy as sa
import re
from collections import defaultdict

# revision identifiers, used by Alembic.
revision = '5b41f80ae7df'
down_revision = 'a6d97996ce12'
branch_labels = None
depends_on = None

CHILD_FK_COLUMNS = [
    ('order_items', 'inventory_id'),
    ('invoice_items', 'inventory_id'),
    ('quotation_items', 'inventory_id'),
    ('dispatch_items', 'inventory_id'),
    ('dispatch_items', 'alternate_inventory_id'),
    ('demo_items', 'inventory_item_id'),
    ('procurement_items', 'inventory_id'),
    ('price_list_items', 'inventory_id'),
]

SI_RE = re.compile(r'^SI\s+(\d+)$', re.IGNORECASE)
BARE_RE = re.compile(r'^\d+$')


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, sku, unit_price, stock_quantity FROM inventory"
    )).fetchall()

    groups = defaultdict(list)
    for r in rows:
        sku = r.sku.strip()
        m = SI_RE.match(sku)
        if m:
            groups[m.group(1)].append(('si', r))
        elif BARE_RE.match(sku):
            groups[sku].append(('bare', r))

    merged_groups = 0
    skipped_groups = []

    for core, members in groups.items():
        if len(members) != 2:
            if len(members) > 2:
                skipped_groups.append((core, [(r.id, r.sku) for _, r in members]))
            continue

        kinds = {kind for kind, _ in members}
        if kinds != {'si', 'bare'}:
            skipped_groups.append((core, [(r.id, r.sku) for _, r in members]))
            continue

        keeper = next(r for kind, r in members if kind == 'si')
        loser = next(r for kind, r in members if kind == 'bare')

        for table, col in CHILD_FK_COLUMNS:
            conn.execute(
                sa.text(f"UPDATE {table} SET {col} = :keeper_id WHERE {col} = :loser_id"),
                {"keeper_id": keeper.id, "loser_id": loser.id},
            )
        conn.execute(sa.text("DELETE FROM inventory WHERE id = :id"), {"id": loser.id})

        new_stock = (keeper.stock_quantity or 0) + (loser.stock_quantity or 0)
        conn.execute(
            sa.text("UPDATE inventory SET stock_quantity = :stock WHERE id = :id"),
            {"stock": new_stock, "id": keeper.id},
        )
        merged_groups += 1

    print(f"merge_si_prefix_duplicate_inventory_skus: merged {merged_groups} groups, "
          f"skipped {len(skipped_groups)} groups")
    for core, members in skipped_groups:
        print(f"  SKIPPED {core}: {members}")


def downgrade() -> None:
    raise NotImplementedError(
        "This data merge is not reversible; restore inventory-related tables "
        "from a pre-migration backup instead."
    )
