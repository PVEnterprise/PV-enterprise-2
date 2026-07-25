"""merge duplicate inventory SKUs (space vs no-space catalog numbers)

Revision ID: cd7303da9eab
Revises: u6v7w8x9y0z1
Create Date: 2026-07-25 14:00:00.000000

Background: many items were entered twice under two SKU spellings that
differ only in whitespace (e.g. "12 0000" vs "120000"). The earlier
(lowest created_at) row is the Inventory team's original entry and holds
the correct stock_quantity; a later duplicate was added by the Pricing
team under a slightly different SKU spelling and holds the correct
unit_price. For each such pair/group this migration keeps the earliest
row, copies the most recent row's unit_price onto it, repoints any
order/invoice/quotation/dispatch/demo/procurement/price-list references
from the later row(s) onto the kept row, then deletes the later row(s).
"""
from alembic import op
import sqlalchemy as sa
import re
from collections import defaultdict

# revision identifiers, used by Alembic.
revision = 'cd7303da9eab'
down_revision = 'u6v7w8x9y0z1'
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


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, sku, unit_price, created_at FROM inventory"
    )).fetchall()

    groups = defaultdict(list)
    for r in rows:
        norm = re.sub(r'\s+', '', r.sku).upper()
        groups[norm].append(r)

    merged_groups = 0
    deleted_rows = 0
    for norm, group in groups.items():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda r: r.created_at)
        keeper = group[0]
        latest_price = group[-1].unit_price

        for loser in group[1:]:
            for table, col in CHILD_FK_COLUMNS:
                conn.execute(
                    sa.text(f"UPDATE {table} SET {col} = :keeper_id WHERE {col} = :loser_id"),
                    {"keeper_id": keeper.id, "loser_id": loser.id},
                )
            conn.execute(
                sa.text("DELETE FROM inventory WHERE id = :id"),
                {"id": loser.id},
            )
            deleted_rows += 1

        conn.execute(
            sa.text("UPDATE inventory SET unit_price = :price WHERE id = :id"),
            {"price": latest_price, "id": keeper.id},
        )
        merged_groups += 1

    print(f"merge_duplicate_inventory_skus: merged {merged_groups} groups, deleted {deleted_rows} rows")


def downgrade() -> None:
    raise NotImplementedError(
        "This data merge is not reversible; restore inventory-related tables "
        "from a pre-migration backup instead."
    )
