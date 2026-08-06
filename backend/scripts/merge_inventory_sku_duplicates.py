"""
One-off fixer: merge duplicate inventory rows created when the sku-spacing
fix was imported via the Import Excel UI before skus were renamed in place.

BACKGROUND
----------
inventory.sku lost the space between the 2-digit series prefix and the
4-digit body for a batch of items (e.g. "120008" instead of "12 0008"),
plus some CC/Ti suffix casing/spacing drift. A corrected Excel export was
then run through the existing Import Excel feature, which upserts by an
EXACT sku string match (POST /inventory/upsert). Since "120008" != "12 0008"
as strings, that import didn't fix the old rows - it CREATED a second row
per changed item, so now there are duplicate pairs: one row on the old
(broken) sku, one row on the new (corrected) sku, describing the same
physical item.

RULE: the OLD row always wins. It's the original, pre-import row and the
one most likely linked from real transaction history (orders, quotations,
invoices, dispatch, demo items, price lists, procurement all point at
inventory.id, never at sku). For each duplicate pair:
  1. Every FK reference pointing at the NEW row's id is re-pointed to the
     OLD row's id.
  2. The new row is deleted.
  3. The old row's sku is set to the normalized value (e.g. "120008" -> "12 0008").

No business fields (price, stock, description, bags, ...) are touched or
merged here. If you want the corrected Excel's price/stock/bag values
applied, re-run the Import Excel UI action AFTER this script - it upserts
by sku, so once the old row's sku matches, that import will update it in
place instead of creating another duplicate.

This does NOT touch any row that doesn't have a duplicate counterpart
(including the small number of pre-existing duplicate skus that predate
this whole spacing bug - those aren't in scope here and need separate,
manual handling).

USAGE
-----
    # Dry run (default) - prints/writes the report, commits nothing
    python backend/scripts/merge_inventory_sku_duplicates.py --report /tmp/merge_report.csv

    # Apply for real, after reviewing the dry-run report
    python backend/scripts/merge_inventory_sku_duplicates.py --apply --report /tmp/merge_report.csv

Back up the database before running with --apply against any environment
that matters. Uses the DB connection from the environment this is run in
(app.db.session / app.core.config.settings) - point your env at prod's
DATABASE_URL before running with --apply against prod.
"""
import argparse
import csv as csv_module
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.inventory import Inventory
from app.models.order import OrderItem
from app.models.quotation import QuotationItem
from app.models.invoice import InvoiceItem
from app.models.dispatch import DispatchItem
from app.models.demo_item import DemoItem
from app.models.price_list import PriceListItem
from app.models.procurement import ProcurementItem


PAT = re.compile(r'^(\d{2})(\s?)(\d{4})(.*)$')
CC_PAT = re.compile(r'^\s?[Cc][Cc]$')
TI_PAT = re.compile(r'^\s?[Tt][Ii]$')

# (label, model, fk_column)
FK_REFS = [
    ("order_items", OrderItem, OrderItem.inventory_id),
    ("quotation_items", QuotationItem, QuotationItem.inventory_id),
    ("invoice_items", InvoiceItem, InvoiceItem.inventory_id),
    ("dispatch_items.inventory_id", DispatchItem, DispatchItem.inventory_id),
    ("dispatch_items.alternate_inventory_id", DispatchItem, DispatchItem.alternate_inventory_id),
    ("demo_items", DemoItem, DemoItem.inventory_item_id),
    ("price_list_items", PriceListItem, PriceListItem.inventory_id),
    ("procurement_items", ProcurementItem, ProcurementItem.inventory_id),
]


def normalize_sku(sku: str) -> str:
    m = PAT.match(sku)
    if not m:
        return sku
    g1, _sp, g2, rest = m.groups()
    if CC_PAT.match(rest):
        new_rest = 'CC'
    elif TI_PAT.match(rest):
        new_rest = 'Ti'
    else:
        stripped = rest.strip()
        if stripped == 'A':
            new_rest = ' A'
        elif stripped == 'V':
            new_rest = ' V'
        else:
            new_rest = rest
    return g1 + ' ' + g2 + new_rest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Actually commit changes. Omit for a dry run.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N pairs (for testing).")
    parser.add_argument("--report", default=None, help="Path to write the CSV report. Defaults to stdout only.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Inventory.id, Inventory.sku).all()
        by_sku = {sku: inv_id for inv_id, sku in rows if sku is not None}

        pairs = []  # (old_id, old_sku, new_id, new_sku)
        for old_id, old_sku in rows:
            if old_sku is None:
                continue
            new_sku = normalize_sku(old_sku)
            if new_sku == old_sku:
                continue
            new_id = by_sku.get(new_sku)
            if new_id is not None and new_id != old_id:
                pairs.append((old_id, old_sku, new_id, new_sku))

        if args.limit:
            pairs = pairs[:args.limit]

        report = []
        merged = 0
        for old_id, old_sku, new_id, new_sku in pairs:
            try:
                with db.begin_nested():
                    moved = {}
                    for label, model, col in FK_REFS:
                        n = db.query(model).filter(col == new_id).update(
                            {col: old_id}, synchronize_session=False
                        )
                        if n:
                            moved[label] = n

                    # Core-level delete, not db.delete(instance): an ORM-instance
                    # delete makes SQLAlchemy load every relationship back-
                    # populated from Inventory (demo_items, dispatch_items, ...)
                    # to evaluate cascade behavior, even though we've already
                    # re-pointed every FK away from new_id above.
                    db.query(Inventory).filter(Inventory.id == new_id).delete(synchronize_session=False)
                    db.query(Inventory).filter(Inventory.id == old_id).update(
                        {Inventory.sku: new_sku}, synchronize_session=False
                    )

                merged += 1
                report.append({
                    "kept_id": str(old_id),
                    "deleted_id": str(new_id),
                    "old_sku": old_sku,
                    "final_sku": new_sku,
                    "fk_refs_moved": "; ".join(f"{k}={v}" for k, v in moved.items()) or "none",
                    "action": "merged",
                })
            except Exception as exc:
                db.rollback()
                report.append({
                    "kept_id": str(old_id), "deleted_id": str(new_id),
                    "old_sku": old_sku, "final_sku": new_sku,
                    "fk_refs_moved": "",
                    "action": f"skipped_error: {type(exc).__name__}: {exc}",
                })

        print(f"\n{'DRY RUN' if not args.apply else 'APPLY'} summary: "
              f"{len(pairs)} duplicate pairs found -> {merged} merged, "
              f"{len(pairs) - merged} skipped (error)\n")

        errored = [r for r in report if r["action"] != "merged"]
        if errored:
            print(f"--- Errors ({len(errored)}) ---")
            for r in errored:
                print(f"  {r['old_sku']!r} / {r['final_sku']!r}: {r['action']}")
            print()

        if args.report:
            with open(args.report, "w", newline="") as f:
                writer = csv_module.DictWriter(f, fieldnames=[
                    "kept_id", "deleted_id", "old_sku", "final_sku", "fk_refs_moved", "action",
                ])
                writer.writeheader()
                writer.writerows(report)
            print(f"Report written to {args.report}")

        if args.apply:
            db.commit()
            print("\nChanges committed.")
        else:
            db.rollback()
            print("\nDry run - no changes were committed. Re-run with --apply once this looks right.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
