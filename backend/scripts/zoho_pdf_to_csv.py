"""
Parse a Zoho "TAX INVOICE" PDF export into a line-item CSV matching the
column names import_zoho_invoices.py already knows how to read (Invoice
Number, Invoice Date, ...). Zoho only offers PDF export for this data (no
CSV/API access on the current plan), so this is the PDF -> CSV bridge feeding
that importer.

USAGE
-----
    python backend/scripts/zoho_pdf_to_csv.py --pdf "APR invoices.pdf" \
        --out-csv zoho_apr_invoices.csv --out-flags zoho_apr_flags.txt

Handles:
- Invoices spanning multiple physical PDF pages (header fields only on the
  first page of the invoice; item rows continue on following pages until
  the next invoice's header appears).
- Two tax layouts: CGST+SGST (intra-state) and IGST (inter-state).
- A Discount column that Zoho only renders when at least one line has a
  non-zero discount.
- Line items with no real catalog code (rare) - flagged with an empty SKU
  rather than guessed, so the DB importer's "SKU not found" check catches
  them for manual review instead of silently mis-mapping.
- Catalog-code formatting quirks are NOT resolved here - that lookup lives
  in import_zoho_invoices.py's resolve_inventory(), since it depends on the
  live Inventory table, not the PDF.

Always spot-check a sample of invoices in the output CSV against the source
PDF before feeding it to the importer - this is regex/table-position based
extraction against a fixed-layout PDF, not a guaranteed-correct OCR result.
"""
import argparse
import csv
import re

import pdfplumber

INVOICE_HEADER_RE = re.compile(r"#\s*:\s*(\S+)\s+Place Of Supply", re.MULTILINE)
INVOICE_DATE_RE = re.compile(r"Invoice Date\s*:\s*([\d]{1,2}\s+\w+\s+\d{4})")
DUE_DATE_RE = re.compile(r"Due Date\s*:\s*([\d]{1,2}\s+\w+\s+\d{4})")
PO_RE = re.compile(r"P\.O\.#\s*:\s*(\S.*)")
TERMS_RE = re.compile(r"Terms\s*:\s*(\S.*)")
SUBTOTAL_RE = re.compile(r"Sub Total\s+([\d,]+\.\d{2})")
GRAND_TOTAL_RE = re.compile(r"Total\s*₹([\d,]+\.\d{2})")
BALANCE_DUE_RE = re.compile(r"Balance Due\s*₹([\d,]+\.\d{2})")

NUMERIC_FRAGMENT_RE = re.compile(r"^-?[\d,]+\.?\d*%?$")


def to_decimal_str(s: str) -> str:
    return s.replace(",", "").strip()


def looks_like_sku(s: str) -> bool:
    """
    Real catalog codes seen in this data always contain a digit ('120006',
    'SI 180', 'BHC 9100', 'SK-19-5-1(f)', '170110Ti') and are short (<=3
    tokens). Two false-positive traps to guard against: a bare brand tag
    like 'SREEDEVI-INDIA' sometimes appears as the first line with no code
    at all (single token, no digit - excluded since digits are required),
    and a dimension like 'Bone Nibbler 9.5"' also has a digit but is
    plainly a description (excluded via the inch-mark check).
    """
    s = s.strip()
    if not s or '"' in s:
        return False
    tokens = s.split()
    has_digit = any(ch.isdigit() for ch in s)
    return has_digit and len(tokens) <= 3


def join_wrapped_number(cell) -> str:
    """
    pdfplumber sometimes splits a single number across cell lines because
    the PDF wraps it mid-digit, e.g. '87,384.0\\n0' -> '87,384.00', or even
    '15,40,75\\n5.00' -> '15,40,755.00' (splitting before the decimal, not
    after it - a naive "is the first fragment already a complete number"
    check gets this one wrong, since '15,40,75' alone also parses as a
    valid Indian-grouped integer). The only robust rule: concatenate the
    RAW fragments (commas intact) when there's more than one numeric-looking
    line, so digit grouping is never broken by string manipulation, and only
    strip commas at the very end.
    """
    if cell is None:
        return ""
    parts = [p.strip() for p in str(cell).split("\n") if p.strip()]
    if not parts:
        return ""
    numeric_frags = [p for p in parts if NUMERIC_FRAGMENT_RE.match(p)]
    if not numeric_frags:
        return parts[0]
    if len(numeric_frags) == 1:
        return numeric_frags[0]
    return "".join(numeric_frags)


def is_item_row(row) -> bool:
    if len(row) < 4:
        return False
    idx_cell = row[1]
    return idx_cell is not None and str(idx_cell).strip().isdigit()


def parse_item_row(row):
    desc_block = str(row[2] or "")
    lines = [l.strip() for l in desc_block.split("\n") if l.strip()]
    if not lines:
        return None
    sku = ""
    description = " ".join(lines)
    if looks_like_sku(lines[0]):
        sku = lines[0]
        description = " ".join(lines[1:]) if len(lines) > 1 else lines[0]

    # Remaining cells after description; row[3] is the HSN/SAC cell (skipped).
    rest = [c for c in row[4:] if c is not None]
    if not rest:
        return None

    qty_str = join_wrapped_number(rest[0])
    try:
        qty = float(to_decimal_str(qty_str))
    except ValueError:
        return None

    if len(rest) < 2:
        return None
    rate_str = join_wrapped_number(rest[1])
    try:
        rate = float(to_decimal_str(rate_str))
    except ValueError:
        return None

    # Scan the remaining cells for %-values (discount + tax rates) and
    # amount-looking values (tax amounts + line amount). The last
    # numeric-looking cell in the row is always the line Amount.
    percent_vals = []
    amount_vals = []
    for c in rest[2:]:
        s = join_wrapped_number(c)
        if s.endswith("%"):
            try:
                percent_vals.append(float(s.rstrip("%")))
            except ValueError:
                pass
        else:
            s_num = to_decimal_str(s)
            if re.match(r"^-?[\d,]+\.\d{2}$", s.strip()) or re.match(r"^-?[\d.]+$", s_num):
                try:
                    amount_vals.append(float(s_num))
                except ValueError:
                    pass

    line_amount = amount_vals[-1] if amount_vals else round(qty * rate, 2)
    # First % value is Discount when 2+ are present (discount + tax legs);
    # CGST+SGST render as two separate tax % entries, IGST as one - either
    # way, everything after the first % is tax. If only one % is present,
    # this invoice rendered no Discount column at all (0% discount), so the
    # single value is pure tax.
    if len(percent_vals) >= 2:
        discount_pct = percent_vals[0]
        tax_pct = sum(percent_vals[1:])
    elif len(percent_vals) == 1:
        discount_pct = 0.0
        tax_pct = percent_vals[0]
    else:
        discount_pct = 0.0
        tax_pct = 0.0

    return {
        "sku": sku,
        "description": description,
        "quantity": qty,
        "unit_price": rate,
        "discount_pct": discount_pct,
        "tax_pct": tax_pct,
        "line_amount": line_amount,
    }


class InvoiceBlock:
    def __init__(self, start_page_idx):
        self.start_page_idx = start_page_idx
        self.page_texts = []
        self.tables = []


def group_pages(pdf):
    """
    Group physical pages into invoices. A page starts a new invoice if it
    has the '# : <number> Place Of Supply' header line; otherwise it's a
    continuation of the most recently started invoice (item rows and/or the
    closing totals/bank-details block).
    """
    blocks = []
    current = None
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if INVOICE_HEADER_RE.search(text):
            current = InvoiceBlock(i)
            blocks.append(current)
        if current is None:
            continue
        current.page_texts.append(text)
        tables = page.extract_tables()
        if tables:
            current.tables.extend(tables)
    return blocks


def extract_invoice(block: InvoiceBlock, flags: list):
    full_text = "\n".join(block.page_texts)

    m = INVOICE_HEADER_RE.search(full_text)
    invoice_number = m.group(1) if m else None
    if not invoice_number:
        flags.append(f"page {block.start_page_idx + 1}: could not find invoice number, skipping block")
        return None

    m = INVOICE_DATE_RE.search(full_text)
    invoice_date = m.group(1) if m else None
    m = DUE_DATE_RE.search(full_text)
    due_date = m.group(1) if m else invoice_date
    m = PO_RE.search(full_text)
    po_number = m.group(1).strip() if m else ""
    m = TERMS_RE.search(full_text)
    payment_terms = m.group(1).strip() if m else ""

    m = SUBTOTAL_RE.search(full_text)
    invoice_subtotal = to_decimal_str(m.group(1)) if m else ""
    m = GRAND_TOTAL_RE.search(full_text)
    invoice_total = to_decimal_str(m.group(1)) if m else ""
    m = BALANCE_DUE_RE.search(full_text)
    balance_due = to_decimal_str(m.group(1)) if m else ""

    if not invoice_subtotal or not invoice_total:
        flags.append(
            f"invoice {invoice_number} (page {block.start_page_idx + 1}): "
            f"missing Sub Total / Total in text - importer will compute from line items"
        )

    # Customer name: find the 'Bill To' marker cell in any table, use the
    # next row's first populated cell, first line.
    customer_name = ""
    for table in block.tables:
        for ridx, row in enumerate(table):
            if any(c is not None and str(c).strip() == "Bill To" for c in row):
                if ridx + 1 < len(table):
                    for c in table[ridx + 1]:
                        if c:
                            customer_name = str(c).split("\n")[0].strip()
                            break
                break
        if customer_name:
            break
    if not customer_name:
        flags.append(f"invoice {invoice_number}: could not find customer name")

    status = "Paid"
    if balance_due and invoice_total:
        try:
            bd, tot = float(balance_due), float(invoice_total)
            if bd <= 0.01:
                status = "Paid"
            elif abs(bd - tot) < 0.01:
                status = "Unpaid"
            else:
                status = "Partial"
        except ValueError:
            pass

    items = []
    for table in block.tables:
        for row in table:
            if is_item_row(row):
                parsed = parse_item_row(row)
                if parsed:
                    items.append(parsed)
                else:
                    flags.append(f"invoice {invoice_number}: could not parse item row {row}")

    if not items:
        flags.append(f"invoice {invoice_number} (page {block.start_page_idx + 1}): no line items found")
        return None

    no_sku_count = sum(1 for it in items if not it["sku"])
    if no_sku_count:
        flags.append(f"invoice {invoice_number}: {no_sku_count} of {len(items)} line(s) have no recognizable SKU")

    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "po_number": po_number,
        "payment_terms": payment_terms,
        "customer_name": customer_name,
        "invoice_subtotal": invoice_subtotal,
        "invoice_total": invoice_total,
        "balance": balance_due,
        "invoice_status": status,
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", required=True, help="Path to the Zoho invoice PDF export")
    parser.add_argument("--out-csv", required=True, help="Where to write the line-item CSV")
    parser.add_argument("--out-flags", required=True, help="Where to write the extraction-flags log")
    args = parser.parse_args()

    with pdfplumber.open(args.pdf) as pdf:
        blocks = group_pages(pdf)

    flags = []
    invoices = []
    for block in blocks:
        inv = extract_invoice(block, flags)
        if inv:
            invoices.append(inv)

    rows = []
    for inv in invoices:
        for item in inv["items"]:
            rows.append({
                "Invoice Number": inv["invoice_number"],
                "Invoice Date": inv["invoice_date"],
                "Due Date": inv["due_date"],
                "Invoice Status": inv["invoice_status"],
                "Customer Name": inv["customer_name"],
                "PO Number": inv["po_number"],
                "Payment Terms": inv["payment_terms"],
                "SKU": item["sku"],
                "Item Name": item["description"],
                "Quantity": item["quantity"],
                "Item Price": item["unit_price"],
                "Item Tax Percent": item["tax_pct"],
                "Line Discount %": item["discount_pct"],
                "Line Amount": item["line_amount"],
                "Sub Total": inv["invoice_subtotal"],
                "Total": inv["invoice_total"],
                "Balance": inv["balance"],
            })

    if rows:
        with open(args.out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    with open(args.out_flags, "w") as f:
        f.write(f"{len(blocks)} invoice blocks detected, {len(invoices)} parsed successfully, {len(flags)} flags\n\n")
        f.write("\n".join(flags))

    print(f"{len(blocks)} invoice blocks detected across {sum(len(b.page_texts) for b in blocks)} pages")
    print(f"{len(invoices)} invoices parsed, {len(rows)} line-item rows written to {args.out_csv}")
    print(f"{len(flags)} flags written to {args.out_flags}")


if __name__ == "__main__":
    main()
