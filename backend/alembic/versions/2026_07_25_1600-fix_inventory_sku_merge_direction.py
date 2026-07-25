"""fix inventory SKU merge direction (correct format/price selection)

Revision ID: a6d97996ce12
Revises: cd7303da9eab
Create Date: 2026-07-25 16:00:00.000000

The prior migration (cd7303da9eab) picked the keeper row by earliest
created_at, assuming that always corresponded to the correctly-formatted
SKU ("12 0000" style). On real prod data that assumption did not hold,
so it kept the wrong SKU format/price for many groups. This migration
supersedes it with the actual rule: the SKU matching "<2 digits><space>"
(e.g. "12 0000", "12 0002CC") is the correct one and keeps its own
stock_quantity; the other SKU in the pair holds the correct unit_price,
which gets copied onto the keeper before the other row is deleted.

Idempotent-safe re: shape - only acts on groups that still have >1 row
for a given whitespace-normalized SKU; already-correct singles are left
alone. Groups where the SKU-format rule can't cleanly pick a keeper (no
row matches the pattern, or more than one does) fall back to picking
the row with a non-placeholder (!= 1000.00) price if exactly one such
row exists. Groups still ambiguous after that (e.g. multiple rows with
different real prices/descriptions) are left untouched for manual
review.
"""
from alembic import op
import sqlalchemy as sa
import re
from collections import defaultdict

# revision identifiers, used by Alembic.
revision = 'a6d97996ce12'
down_revision = 'cd7303da9eab'
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

SPACED_RE = re.compile(r'^\d{2} ')


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, sku, unit_price FROM inventory"
    )).fetchall()

    groups = defaultdict(list)
    for r in rows:
        norm = re.sub(r'\s+', '', r.sku).upper()
        groups[norm].append(r)

    merged_groups = 0
    deleted_rows = 0
    skipped_groups = []

    for norm, group in groups.items():
        if len(group) < 2:
            continue

        spaced = [r for r in group if SPACED_RE.match(r.sku.strip())]
        not_spaced = [r for r in group if not SPACED_RE.match(r.sku.strip())]

        if len(spaced) == 1 and len(not_spaced) == 1:
            keeper = spaced[0]
            losers = not_spaced
            correct_price = losers[0].unit_price
        else:
            non_placeholder = [r for r in group if r.unit_price != 1000.0]
            if len(non_placeholder) == 1:
                keeper = non_placeholder[0]
                losers = [r for r in group if r is not keeper]
                correct_price = keeper.unit_price  # already correct, no price copy needed
            else:
                skipped_groups.append((norm, [(r.id, r.sku, r.unit_price) for r in group]))
                continue

        for loser in losers:
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

        if keeper.unit_price != correct_price:
            conn.execute(
                sa.text("UPDATE inventory SET unit_price = :price WHERE id = :id"),
                {"price": correct_price, "id": keeper.id},
            )
        merged_groups += 1

    print(f"fix_inventory_sku_merge_direction: merged {merged_groups} groups, "
          f"deleted {deleted_rows} rows, skipped {len(skipped_groups)} groups for manual review")
    for norm, members in skipped_groups:
        print(f"  SKIPPED {norm}: {members}")


def downgrade() -> None:
    raise NotImplementedError(
        "This data merge is not reversible; restore inventory-related tables "
        "from a pre-migration backup instead."
    )
