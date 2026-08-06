"""
One-off fixer: normalize inventory.sku spacing/casing in place.

BACKGROUND
----------
A batch of Catalog No values lost the space between the 2-digit series
prefix and the 4-digit body at some point (e.g. "120008" instead of
"12 0008"), and some CC/Ti suffixes drifted in case/spacing (" CC", "cc",
" TI" instead of the canonical "CC"/"Ti" attached with no space). The
correct series shape is "XX XXXX" optionally followed by a suffix such as
"CC", "Ti", "-XX", " A", " V", etc.

This script RENAMES sku in place (UPDATE inventory SET sku = ... WHERE
sku = ...) rather than deleting the old row and creating a new one. Every
foreign key in this codebase (orders, quotations, invoices, dispatch,
demo items, price lists, procurement) points at inventory.id, never at
sku - so a rename preserves history and links; a delete+recreate would
orphan or cascade-delete all of that.

Run this BEFORE importing the corrected inventory Excel through the UI.
The Excel import upserts by exact sku string match (see
POST /inventory/upsert) - if sku isn't fixed here first, the import will
just CREATE new rows for every changed sku and leave the old-spelling
rows behind as stale duplicates.

sku is UNIQUE + NOT NULL. A handful of old skus normalize to a value
that's already used by a different (already-correctly-spelled) row - the
script detects these as collisions and skips them; it never merges or
deletes anything. Review those manually.

USAGE
-----
    # Dry run (default) - prints/writes the report, commits nothing
    python backend/scripts/fix_inventory_sku_spacing.py --report /tmp/sku_fix_report.csv

    # Apply for real, after reviewing the dry-run report
    python backend/scripts/fix_inventory_sku_spacing.py --apply --report /tmp/sku_fix_report.csv

Uses the DB connection from the environment this is run in (app.db.session
/ app.core.config.settings) - point your env at prod's DATABASE_URL
before running with --apply against prod. This script does not know or
assume which environment it's connected to; check that yourself first.
"""
import argparse
import csv as csv_module
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.inventory import Inventory


PAT = re.compile(r'^(\d{2})(\s?)(\d{4})(.*)$')
CC_PAT = re.compile(r'^\s?[Cc][Cc]$')
TI_PAT = re.compile(r'^\s?[Tt][Ii]$')


def normalize_sku(sku: str) -> str:
    """Mirrors the exact transform applied to the corrected Excel export."""
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
    parser.add_argument("--report", default=None, help="Path to write the CSV report. Defaults to stdout only.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Inventory.id, Inventory.sku).all()
        all_skus = {sku for _id, sku in rows}

        planned = []       # (id, old_sku, new_sku)
        collisions = []    # (id, old_sku, new_sku, reason)
        seen_targets = {}  # new_sku -> old_sku, to catch two old skus colliding with each other

        for inv_id, sku in rows:
            if sku is None:
                continue
            new_sku = normalize_sku(sku)
            if new_sku == sku:
                continue
            if new_sku in all_skus and new_sku != sku:
                collisions.append((inv_id, sku, new_sku, f"target sku already exists on another row"))
                continue
            if new_sku in seen_targets:
                collisions.append((inv_id, sku, new_sku, f"also produced by sku '{seen_targets[new_sku]}' in this same run"))
                continue
            seen_targets[new_sku] = sku
            planned.append((inv_id, sku, new_sku))

        report = []
        renamed = 0
        for inv_id, old_sku, new_sku in planned:
            try:
                with db.begin_nested():
                    inv = db.query(Inventory).filter(Inventory.id == inv_id).with_for_update().one()
                    inv.sku = new_sku
                renamed += 1
                report.append({"id": str(inv_id), "old_sku": old_sku, "new_sku": new_sku, "action": "renamed"})
            except IntegrityError as exc:
                db.rollback()
                report.append({"id": str(inv_id), "old_sku": old_sku, "new_sku": new_sku, "action": f"skipped_error: {exc.orig}"})

        for inv_id, old_sku, new_sku, reason in collisions:
            report.append({"id": str(inv_id), "old_sku": old_sku, "new_sku": new_sku, "action": f"skipped_collision: {reason}"})

        print(f"\n{'DRY RUN' if not args.apply else 'APPLY'} summary: "
              f"{len(rows)} inventory rows scanned -> {renamed} renamed, "
              f"{len(collisions)} skipped (collision), "
              f"{len(planned) - renamed} skipped (error)\n")

        if collisions:
            print(f"--- Collisions requiring manual review ({len(collisions)}) ---")
            for inv_id, old_sku, new_sku, reason in collisions:
                print(f"  {old_sku!r:20s} -> {new_sku!r:20s} [{reason}] (id={inv_id})")
            print()

        if args.report:
            with open(args.report, "w", newline="") as f:
                writer = csv_module.DictWriter(f, fieldnames=["id", "old_sku", "new_sku", "action"])
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
