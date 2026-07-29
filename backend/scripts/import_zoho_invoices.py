"""
One-off importer: backfill historical Zoho invoices into PV Enterprise.

USAGE
-----
    # Show which export columns were detected before running anything real
    python backend/scripts/import_zoho_invoices.py --file zoho_export.csv --show-columns

    # Dry run (default) - builds every record in memory, validates it,
    # prints/writes a report, then rolls back. No DB writes.
    python backend/scripts/import_zoho_invoices.py --file zoho_export.csv \
        --user-email exec@pventerprise.com --report /tmp/zoho_import_report.csv

    # Apply for real, after reviewing the dry-run report
    python backend/scripts/import_zoho_invoices.py --file zoho_export.csv \
        --user-email exec@pventerprise.com --apply

INPUT
-----
A Zoho Books invoice export (CSV or XLSX) at LINE-ITEM granularity - one row
per invoice line, with invoice-level fields (Invoice Number, Invoice Date,
Customer Name, ...) repeated on every row belonging to the same invoice.
This is what Zoho Books produces exporting Invoices with item details
included.

Column names are matched case/spacing-insensitively against the aliases in
COLUMN_ALIASES below. Run with --show-columns first against a real export
and adjust COLUMN_ALIASES if a column isn't picked up - don't rename the
export file to work around it.

WHAT THIS SCRIPT DOES, per distinct invoice number in the file
----------------------------------------------------------------
1. Skip if Dispatch.invoice_number already has an exact-string match. This
   is the field the live UI/invoice PDF actually searches by (confirmed via
   GET /dispatches/invoices), even though it carries no DB uniqueness
   constraint today.
2. Find-or-create the Customer by hospital_name (same exact-match rule the
   existing /customers/import-excel endpoint uses).
3. Resolve every line item's Inventory row by SKU (= Zoho's Catalog No,
   confirmed identical across both systems). A missing SKU is a hard error
   for that invoice - the whole invoice is skipped and reported, never
   silently invented or partially imported.
4. Create Order + OrderItems, Quotation + QuotationItems, Invoice +
   InvoiceItems, and Dispatch + DispatchItems, written directly in a
   terminal state (workflow_stage="completed"), bypassing the live
   multi-role approval chain - these are historical, already-settled
   transactions, not new work awaiting sign-off.
5. Stock quantities are NEVER touched. These shipments already happened;
   backfilling them must not move today's live stock count.

Financial totals (subtotal / GST / total) are taken directly from the
invoice-level columns in the export when present, not recomputed from line
items, so the imported record matches what Zoho actually invoiced. If those
columns aren't found, totals are computed from line items and every such
invoice is flagged in the report as "totals_computed" so you can spot-check
it against the original Zoho PDF.

Everything runs inside one DB transaction per invoice (a SAVEPOINT), so one
bad row never corrupts a sibling invoice, and the whole run is one
transaction that's rolled back at the end unless --apply is passed.
"""
import argparse
import csv as csv_module
import re
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.dispatch import Dispatch, DispatchItem
from app.models.inventory import Inventory
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, OrderItem
from app.models.quotation import Quotation, QuotationItem
from app.models.user import User

from app.api.v1.endpoints.orders import generate_order_number
from app.api.v1.endpoints.quotations import generate_quote_number
from app.api.v1.endpoints.dispatches import generate_dispatch_number


# Canonical field -> acceptable header aliases (matched after the header is
# stripped, lowercased, and spaces/punctuation collapsed to underscores).
# Adjust/extend this once you've run --show-columns against a real export.
COLUMN_ALIASES = {
    "invoice_number": ["invoice_number", "invoice_no", "invoice_#", "invoice#"],
    "invoice_date": ["invoice_date"],
    "due_date": ["due_date", "expected_payment_date"],
    "invoice_status": ["invoice_status", "status"],
    "balance": ["balance"],
    "customer_name": ["customer_name", "customer", "company_name"],
    "customer_address": ["customer_address", "address"],
    "customer_city": ["customer_city", "city"],
    "customer_state": ["customer_state", "state"],
    "customer_pincode": ["customer_pincode", "pincode", "pin_code", "postal_code"],
    "customer_gst": ["customer_gst_number", "customer_gst", "gst_number", "gstin"],
    "po_number": ["purchaseorder", "po_number", "purchase_order", "po_#"],
    "payment_terms": ["payment_terms", "terms"],
    "sku": ["sku", "product_id", "item_sku", "catalog_no", "catalog_number"],
    "item_description": ["item_name", "item_desc", "item_description", "description"],
    "quantity": ["quantity", "qty"],
    "unit_price": ["item_price", "rate", "price", "unit_price"],
    "item_tax_percent": ["item_tax_%", "item_tax_percent", "tax_%", "gst_%", "gst_percentage"],
    "invoice_subtotal": ["sub_total", "subtotal"],
    "invoice_total": ["total", "invoice_total"],
}

REQUIRED_FIELDS = [
    "invoice_number", "invoice_date", "customer_name",
    "sku", "item_description", "quantity", "unit_price",
]


def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def match_columns(df: pd.DataFrame) -> dict:
    detected = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                detected[canonical] = alias
                break
    return detected


def parse_decimal(value) -> Decimal:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return Decimal("0")
    s = str(value).strip().replace(",", "").replace("₹", "")
    if s == "" or s.lower() == "nan":
        return Decimal("0")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Could not parse decimal from {value!r}")


def parse_date(value) -> date:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(str(value).strip(), dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def sku_candidates(raw_sku: str) -> list:
    """
    Zoho's exported item code and this app's Inventory.sku don't always
    match verbatim. Confirmed against the real catalog:
    - Numeric codes are stored with a space after the first 2 digits
      ('120006' in Zoho is '12 0006' here). Any trailing letter suffix
      (CC/Ti/A/...) is inconsistently spaced in the catalog itself -
      '12 0004CC' has no space, but '17 0502 A' does - so both variants
      are tried rather than guessing one rule.
    - Spacing around any code is inconsistent catalog-wide (single space,
      double space, or none - e.g. 'SLS 11600' is 'SLS11600', 'SLS 9110'
      is 'SLS  9110' with two spaces) - so the fully space-stripped
      "compact" form is always tried too.
    - The digits alone (whether bare, e.g. '9100', or under a wrong/stale
      brand prefix Zoho still uses internally, e.g. 'BHC 9100') often
      belong to the 'SLS' catalog family (anaesthesia/perfusion
      consumables) - 'BHC' does not exist as a prefix in Inventory at all
      (confirmed: zero rows), every 'BHC ####' code checked so far is
      really 'SLS ####' with the same digits. Tried as a last resort.
    Exact value first, then the transforms, in that order.
    """
    raw_sku = raw_sku.strip()
    candidates = [raw_sku]
    compact = raw_sku.replace(" ", "")
    if compact not in candidates:
        candidates.append(compact)

    m = re.match(r"^(\d{2})(\d+)([A-Za-z].*)?$", compact)
    if m:
        digits_head, digits_tail, suffix = m.group(1), m.group(2), m.group(3) or ""
        for candidate in (
            f"{digits_head} {digits_tail}{suffix}",
            f"{digits_head} {digits_tail} {suffix}" if suffix else None,
        ):
            if candidate and candidate not in candidates:
                candidates.append(candidate)

    m = re.search(r"(\d+)$", compact)
    if m:
        digits = m.group(1)
        for candidate in (f"SLS {digits}", f"SLS{digits}", f"SLS  {digits}"):
            if candidate not in candidates:
                candidates.append(candidate)

    # Catalog casing on trailing letter suffixes is inconsistent too - both
    # '12 0004CC' and '14 0140cc' exist. Try a lowercase-suffix variant of
    # every candidate found so far (cheap and safe: it only adds a new
    # exact-match attempt, never changes which one wins).
    for candidate in list(candidates):
        lowered = re.sub(r"[A-Za-z]+$", lambda mo: mo.group(0).lower(), candidate)
        if lowered not in candidates:
            candidates.append(lowered)

    # The 'SK-' catalog series uses hyphens throughout ('SK-19-5-2(f)'),
    # but Zoho's export sometimes renders the same code with spaces
    # ('SK 19-5 2(f)') - try swapping spaces for hyphens.
    if " " in raw_sku:
        hyphenated = raw_sku.replace(" ", "-")
        if hyphenated not in candidates:
            candidates.append(hyphenated)

    return candidates


DESCRIPTION_NOISE_RE_LIST = [
    (re.compile(r"\(SREEDEVI\)", re.IGNORECASE), ""),
    (re.compile(r"SREEDEVI[- ]INDIA", re.IGNORECASE), ""),
    (re.compile(r"^Sreedevi\s+", re.IGNORECASE), ""),
    (re.compile(r"\(SGS\d+\)", re.IGNORECASE), ""),
    (re.compile(r"\bCVD\b|\bCurved\b", re.IGNORECASE), "Cvd"),
    (re.compile(r"\bSTR\b|\bStraight\b", re.IGNORECASE), "Str"),
    (re.compile(r"\bDouble Action\b", re.IGNORECASE), "D/A"),
    (re.compile(r"\bFiber Handle\b", re.IGNORECASE), "F.H"),
    (re.compile(r"\bVentriculo Peritoneal\b", re.IGNORECASE), "V.P."),
    (re.compile(r"\bStainless Steel\b", re.IGNORECASE), "(S.S)"),
]


def normalize_description(s: str) -> str:
    """
    Some Zoho line items carry no catalog code at all (rare, but real) -
    just a free-text description. Many of these turn out to be catalog
    items sold under this app's own 'SI ####' Sreedevi-branded line, with
    the Zoho description differing only by a brand tag ('(SREEDEVI)',
    'Sreedevi <name>', '<name> SREEDEVI-INDIA') or spelled-out Cvd/Str.
    Strip that noise so both sides can be compared as plain text.
    """
    for pattern, repl in DESCRIPTION_NOISE_RE_LIST:
        s = pattern.sub(repl, s)
    return re.sub(r"\s+", " ", s).strip().lower()


# Descriptions that either (a) resolve to more than one catalog SKU under
# normalize_description() - genuine duplicate catalog entries with the same
# description text but different SKU/price/stock, where a human judgment
# call was made (see git history for the reasoning) - or (b) use different
# wording from the catalog entry entirely, so no text-similarity match is
# possible. Checked first, before the live description search.
DESCRIPTION_SKU_OVERRIDES = {
    normalize_description('Ventilator Tubing with double water trap (SGS25007)'): "SLS 1020",
    normalize_description('Backhaus Towel Clips 5"'): "SI 327",
    normalize_description('Sreedevi Allis Tissue Grasping Forceps 10"'): "SI 139",
    normalize_description('Standard Diss. Forceps Toothed 6"(SREEDEVI)'): "SI 90",
    # Catalog description carries extra trailing text ('(Skin)/Sen Retractor')
    # that a plain normalized-text match can't bridge.
    normalize_description('Catspaw Retractor'): "SI 330",
    # Catalog description carries an extra leading qualifier ('Ross/Vein/').
    normalize_description('Sreedevi Eye Lid Retractor'): "SI 371",
    # Catalog has no space before the trailing Cvd/Str/Ang abbreviation
    # ('91/2"Cvd'), Zoho's export does ('91/2" Cvd') - same spacing
    # inconsistency as SKU suffixes, just on description text this time.
    normalize_description('Sreedevi Codman Leksell Rongeur 91/2" Cvd'): "SI 416",
    normalize_description('Sreedevi Codman Leksell Rongeur 81/2" Cvd'): "SI 413",
    # Catalog description carries an extra qualifier ('( Set of 10)') and a
    # double space.
    normalize_description('Sreedevi Heggars Dilators Set Aluminium'): "SI 325",
    # 'Scalpel handle round 15cm' has no matching text anywhere in the
    # catalog - confirmed with the user this is the scalpel handle sold as
    # a generic B.P (Bard-Parker) handle, size No.3.
    normalize_description('Sreedevi scalpel hdl rd 15cm'): "SI 591",
    # Multi-line kit descriptions (verified by exact unit-price match
    # against the invoice, not just text similarity).
    normalize_description('LA RETRACTOR SET CONSISTING INTERCOSTAL (SREEDEVI)'): "si 683",
    normalize_description('MICS ARCH RETRACTOR SET WITH CONTAINER UPPER CURVED(SREEDEVI)'): "SI 675",
    normalize_description('MICS SCOPE HOLDER TITANIUM ARM (SREEDEVI)'): "si 685",
    # Catalog description has the words in a different order.
    normalize_description('SREEDEVI Hook Nerve Vessel Fine'): "SI 585",
    normalize_description('SREEDEVI Hook nerve Vessel Blunt'): "SI 586",
    # Confirmed directly by the user - catalog description text ('Cooley
    # Coarctation clamp...') doesn't match this item's name at all, but
    # they confirmed the SKU is correct as stored. Not a text-match case.
    normalize_description('Pediatric Ambu Junior Manikin'): "20 0408",
    # Confirmed directly by the user.
    normalize_description('Aortic Cannula Femoral sizes 8,10,12,14, FR (SGS25081)'): "SLS 70212",
    # Confirmed directly by the user.
    normalize_description('Magnetic Sheet Autoclavable'): "SK-31-5-1",
}


def build_description_index(db) -> dict:
    """normalized description -> list of SKUs sharing that normalized text."""
    index = {}
    for sku, desc in db.query(Inventory.sku, Inventory.description).filter(Inventory.description.isnot(None)).all():
        index.setdefault(normalize_description(desc), []).append(sku)
    return index


def resolve_by_description(db, description_index: dict, description: str):
    """Returns (sku_or_None, note_or_None) for a line item with no SKU at all."""
    normalized = normalize_description(description)
    override = DESCRIPTION_SKU_OVERRIDES.get(normalized)
    if override:
        return override, f"matched by description override to '{override}'"
    matches = description_index.get(normalized, [])
    if len(matches) == 1:
        return matches[0], f"matched by description to '{matches[0]}'"
    if len(matches) > 1:
        return None, f"description matches {len(matches)} catalog SKUs ({', '.join(matches)}) - ambiguous, add to DESCRIPTION_SKU_OVERRIDES to resolve"
    return None, None


def resolve_inventory(db, raw_sku: str):
    """Returns (Inventory or None, the candidate string that matched)."""
    for candidate in sku_candidates(raw_sku):
        inventory = db.query(Inventory).filter(Inventory.sku == candidate).first()
        if inventory:
            return inventory, candidate
    return None, None


def get_or_create_customer(db, hospital_name: str, script_user_id, address_fields: dict) -> Customer:
    hospital_name = hospital_name.strip()
    existing = db.query(Customer).filter(Customer.hospital_name == hospital_name).first()
    if existing:
        return existing, False
    customer = Customer(
        hospital_name=hospital_name,
        name=hospital_name,
        address=address_fields.get("address") or None,
        city=address_fields.get("city") or None,
        state=address_fields.get("state") or None,
        pincode=address_fields.get("pincode") or None,
        gst_number=address_fields.get("gst_number") or None,
        created_by=script_user_id,
    )
    db.add(customer)
    db.flush()
    return customer, True


class InvoiceGroup:
    def __init__(self, invoice_number: str):
        self.invoice_number = invoice_number
        self.rows = []
        self.errors = []


def build_groups(df: pd.DataFrame, cols: dict) -> "list[InvoiceGroup]":
    groups_by_number = {}
    order = []
    for _, row in df.iterrows():
        raw_number = row.get(cols["invoice_number"])
        if raw_number is None or (isinstance(raw_number, float) and pd.isna(raw_number)):
            continue
        invoice_number = str(raw_number).strip()
        if not invoice_number:
            continue
        if invoice_number not in groups_by_number:
            groups_by_number[invoice_number] = InvoiceGroup(invoice_number)
            order.append(invoice_number)
        groups_by_number[invoice_number].rows.append(row)
    return [groups_by_number[n] for n in order]


def process_group(db, group: InvoiceGroup, cols: dict, script_user: User, report: list, description_index: dict):
    invoice_number = group.invoice_number

    existing_dispatch = db.query(Dispatch).filter(
        Dispatch.invoice_number == invoice_number
    ).first()
    if existing_dispatch:
        report.append({
            "invoice_number": invoice_number,
            "action": "skipped_duplicate",
            "detail": f"Dispatch {existing_dispatch.dispatch_number} already has this invoice number",
        })
        return

    first = group.rows[0]
    invoice_date = parse_date(first.get(cols["invoice_date"]))
    if not invoice_date:
        report.append({
            "invoice_number": invoice_number,
            "action": "skipped_error",
            "detail": "Could not parse invoice_date",
        })
        return

    due_date = None
    if "due_date" in cols:
        due_date = parse_date(first.get(cols["due_date"]))
    if not due_date or due_date < invoice_date:
        due_date = invoice_date

    customer_name = str(first.get(cols["customer_name"], "")).strip()
    if not customer_name or customer_name.lower() == "nan":
        report.append({
            "invoice_number": invoice_number,
            "action": "skipped_error",
            "detail": "Missing customer name",
        })
        return

    def _clean(field):
        if field not in cols:
            return ""
        val = first.get(cols[field])
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        val = str(val).strip()
        return "" if val.lower() == "nan" else val

    customer_address_fields = {
        "address": _clean("customer_address"),
        "city": _clean("customer_city"),
        "state": _clean("customer_state"),
        "pincode": _clean("customer_pincode"),
        "gst_number": _clean("customer_gst"),
    }

    # Resolve every line item's inventory row up front - a single missing
    # SKU fails the whole invoice rather than importing it partially.
    line_items = []
    for row in group.rows:
        sku = str(row.get(cols["sku"], "")).strip()
        item_description_raw = str(row.get(cols["item_description"], "")).strip()
        if not sku or sku.lower() == "nan":
            matched_sku, note = resolve_by_description(db, description_index, item_description_raw)
            if not matched_sku:
                report.append({
                    "invoice_number": invoice_number,
                    "action": "skipped_error",
                    "detail": f"Row missing SKU: {item_description_raw!r}" + (f" ({note})" if note else ""),
                })
                return
            report.append({
                "invoice_number": invoice_number,
                "action": "note",
                "detail": f"No SKU for {item_description_raw!r} - {note}",
            })
            sku = matched_sku
        inventory, matched_as = resolve_inventory(db, sku)
        if not inventory:
            report.append({
                "invoice_number": invoice_number,
                "action": "skipped_error",
                "detail": f"SKU '{sku}' not found in Inventory catalog (tried: {', '.join(sku_candidates(sku))})",
            })
            return
        if matched_as != sku:
            report.append({
                "invoice_number": invoice_number,
                "action": "note",
                "detail": f"SKU '{sku}' matched Inventory catalog as '{matched_as}'",
            })
        try:
            quantity = int(parse_decimal(row.get(cols["quantity"])))
            unit_price = parse_decimal(row.get(cols["unit_price"]))
        except ValueError as exc:
            report.append({
                "invoice_number": invoice_number,
                "action": "skipped_error",
                "detail": f"SKU '{sku}': {exc}",
            })
            return
        if quantity <= 0:
            report.append({
                "invoice_number": invoice_number,
                "action": "skipped_error",
                "detail": f"SKU '{sku}': non-positive quantity {quantity}",
            })
            return
        gst_percentage = inventory.tax
        if "item_tax_percent" in cols:
            raw_tax = row.get(cols["item_tax_percent"])
            if raw_tax is not None and not (isinstance(raw_tax, float) and pd.isna(raw_tax)):
                try:
                    gst_percentage = parse_decimal(raw_tax)
                except ValueError:
                    pass
        line_items.append({
            "inventory": inventory,
            "description": str(row.get(cols["item_description"], inventory.description or sku)).strip(),
            "quantity": quantity,
            "unit_price": unit_price,
            "gst_percentage": gst_percentage,
        })

    computed_subtotal = sum(li["quantity"] * li["unit_price"] for li in line_items)
    computed_gst = sum(
        li["quantity"] * li["unit_price"] * (li["gst_percentage"] / Decimal("100"))
        for li in line_items
    )

    totals_computed = False
    if "invoice_subtotal" in cols and "invoice_total" in cols:
        try:
            subtotal = parse_decimal(first.get(cols["invoice_subtotal"]))
            total_amount = parse_decimal(first.get(cols["invoice_total"]))
        except ValueError:
            subtotal, total_amount = None, None
        if not subtotal or not total_amount:
            subtotal, total_amount = computed_subtotal, computed_subtotal + computed_gst
            totals_computed = True
        gst_amount = total_amount - subtotal if total_amount >= subtotal else computed_gst
    else:
        subtotal, gst_amount, total_amount = computed_subtotal, computed_gst, computed_subtotal + computed_gst
        totals_computed = True

    discount_percentage = Decimal("0")
    if computed_subtotal > 0 and subtotal < computed_subtotal:
        discount_percentage = ((computed_subtotal - subtotal) / computed_subtotal * 100).quantize(Decimal("0.01"))

    payment_status = "paid"
    paid_amount = total_amount
    if "invoice_status" in cols:
        status_val = str(first.get(cols["invoice_status"], "")).strip().lower()
        if "partial" in status_val:
            payment_status, paid_amount = "partial", (
                total_amount - parse_decimal(first.get(cols.get("balance"), 0)) if "balance" in cols else total_amount
            )
        elif status_val in ("draft", "sent", "overdue", "unpaid", "void"):
            payment_status, paid_amount = "unpaid", Decimal("0")

    customer, customer_created = get_or_create_customer(db, customer_name, script_user.id, customer_address_fields)

    po_number = str(first.get(cols["po_number"], "")).strip() if "po_number" in cols else None
    if po_number and po_number.lower() == "nan":
        po_number = None
    payment_terms = str(first.get(cols["payment_terms"], "")).strip() if "payment_terms" in cols else None
    if payment_terms and payment_terms.lower() == "nan":
        payment_terms = None

    order_number = generate_order_number(db)
    order = Order(
        order_number=order_number,
        customer_id=customer.id,
        sales_rep_id=script_user.id,
        status="completed",
        workflow_stage="completed",
        po_number=po_number,
        discount_percentage=discount_percentage,
        quotation_date=invoice_date,
        notes=f"Imported from Zoho invoice {invoice_number} on {date.today().isoformat()}",
    )
    db.add(order)
    db.flush()

    order_items = []
    for li in line_items:
        oi = OrderItem(
            order_id=order.id,
            item_description=li["description"],
            quantity=li["quantity"],
            inventory_id=li["inventory"].id,
            decoded_by=script_user.id,
            unit_price=li["unit_price"],
            gst_percentage=li["gst_percentage"],
            status="completed",
        )
        db.add(oi)
        order_items.append(oi)
    db.flush()

    quote_number = generate_quote_number(db)
    quotation = Quotation(
        quote_number=quote_number,
        order_id=order.id,
        created_by=script_user.id,
        status="approved",
        subtotal=subtotal,
        gst_amount=gst_amount,
        discount_percentage=discount_percentage,
        discount_amount=(computed_subtotal - subtotal) if computed_subtotal > subtotal else Decimal("0"),
        total_amount=total_amount,
        valid_until=invoice_date,
        payment_terms=payment_terms,
    )
    db.add(quotation)
    db.flush()

    for li, oi in zip(line_items, order_items):
        db.add(QuotationItem(
            quotation_id=quotation.id,
            inventory_id=li["inventory"].id,
            description=li["description"],
            quantity=li["quantity"],
            unit_price=li["unit_price"],
            line_total=li["quantity"] * li["unit_price"],
        ))

    invoice = Invoice(
        invoice_number=invoice_number,
        quotation_id=quotation.id,
        order_id=order.id,
        created_by=script_user.id,
        status="sent",
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        gst_amount=gst_amount,
        total_amount=total_amount,
        paid_amount=paid_amount,
        payment_status=payment_status,
        payment_terms=payment_terms,
    )
    db.add(invoice)
    db.flush()

    for li in line_items:
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            inventory_id=li["inventory"].id,
            description=li["description"],
            quantity=li["quantity"],
            unit_price=li["unit_price"],
            line_total=li["quantity"] * li["unit_price"],
        ))

    dispatch_number = generate_dispatch_number(db)
    dispatch = Dispatch(
        dispatch_number=dispatch_number,
        order_id=order.id,
        invoice_id=invoice.id,
        dispatch_date=invoice_date,
        status="delivered",
        notes="Backfilled from Zoho export - stock not adjusted.",
        payment_terms=payment_terms,
        po_number=po_number,
        invoice_number=invoice_number,
        bank_account_name=customer.bank_account_name,
        bank_account_number=customer.bank_account_number,
        bank_name=customer.bank_name,
        bank_ifsc=customer.bank_ifsc,
        bank_branch=customer.bank_branch,
        created_by=script_user.id,
    )
    db.add(dispatch)
    db.flush()

    for li, oi in zip(line_items, order_items):
        db.add(DispatchItem(
            dispatch_id=dispatch.id,
            order_item_id=oi.id,
            inventory_id=li["inventory"].id,
            quantity=li["quantity"],
        ))
    db.flush()

    report.append({
        "invoice_number": invoice_number,
        "action": "created",
        "detail": (
            f"order={order_number} quote={quote_number} dispatch={dispatch_number} "
            f"customer={'new' if customer_created else 'matched'} "
            f"total={total_amount} discount_pct={discount_percentage}"
            + (" [totals_computed - verify against Zoho PDF]" if totals_computed else "")
        ),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, help="Path to the Zoho export (CSV or XLSX)")
    parser.add_argument("--user-email", help="Email of the user to attribute imported records to (required unless --show-columns)")
    parser.add_argument("--apply", action="store_true", help="Actually commit changes. Omit for a dry run.")
    parser.add_argument("--show-columns", action="store_true", help="Print detected column mapping and exit - no DB access.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N distinct invoices (for testing).")
    parser.add_argument("--report", default=None, help="Path to write the CSV report. Defaults to stdout only.")
    args = parser.parse_args()

    path = Path(args.file)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df = normalize_headers(df)
    cols = match_columns(df)

    if args.show_columns:
        print("Detected column mapping:")
        for canonical, actual in cols.items():
            print(f"  {canonical:20s} <- {actual}")
        missing = [f for f in REQUIRED_FIELDS if f not in cols]
        if missing:
            print(f"\nMISSING required fields: {missing}")
            print(f"All columns in file: {list(df.columns)}")
        return

    missing = [f for f in REQUIRED_FIELDS if f not in cols]
    if missing:
        print(f"ERROR: missing required columns for fields {missing}")
        print(f"All columns in file: {list(df.columns)}")
        print("Run with --show-columns to see the current mapping, and adjust COLUMN_ALIASES if needed.")
        sys.exit(1)

    if not args.user_email:
        print("ERROR: --user-email is required (an existing user to attribute imported records to)")
        sys.exit(1)

    db = SessionLocal()
    try:
        script_user = db.query(User).filter(User.email == args.user_email).first()
        if not script_user:
            print(f"ERROR: no user found with email {args.user_email}")
            sys.exit(1)

        groups = build_groups(df, cols)
        if args.limit:
            groups = groups[:args.limit]

        description_index = build_description_index(db)
        report = []
        for group in groups:
            try:
                with db.begin_nested():
                    process_group(db, group, cols, script_user, report, description_index)
            except IntegrityError as exc:
                db.rollback()
                report.append({
                    "invoice_number": group.invoice_number,
                    "action": "skipped_error",
                    "detail": f"IntegrityError: {exc.orig}",
                })
            except Exception as exc:
                report.append({
                    "invoice_number": group.invoice_number,
                    "action": "skipped_error",
                    "detail": f"{type(exc).__name__}: {exc}",
                })

        created = sum(1 for r in report if r["action"] == "created")
        duplicates = sum(1 for r in report if r["action"] == "skipped_duplicate")
        errors = sum(1 for r in report if r["action"] == "skipped_error")

        print(f"\n{'DRY RUN' if not args.apply else 'APPLY'} summary: "
              f"{len(groups)} invoices processed -> {created} created, "
              f"{duplicates} already existed, {errors} errored\n")
        for r in report:
            print(f"  [{r['action']:18s}] {r['invoice_number']:20s} {r['detail']}")

        skipped = [r for r in report if r["action"] in ("skipped_error", "skipped_duplicate")]
        if skipped:
            print(f"\n--- Skipped invoices ({len(skipped)}) ---")
            for r in sorted(skipped, key=lambda r: r["invoice_number"]):
                print(f"  {r['invoice_number']:20s} [{r['action']}] {r['detail']}")

        if args.report:
            with open(args.report, "w", newline="") as f:
                writer = csv_module.DictWriter(f, fieldnames=["invoice_number", "action", "detail"])
                writer.writeheader()
                writer.writerows(report)
            print(f"\nReport written to {args.report}")

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
