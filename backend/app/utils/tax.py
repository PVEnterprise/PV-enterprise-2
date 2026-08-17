"""Tax label and rounding helpers for invoices and estimates/quotations."""

from decimal import Decimal, ROUND_HALF_UP

HOME_STATE = "telangana"


def get_tax_label(state: str) -> str:
    """
    Return the tax label to display on invoices/estimates.

    Orders billed within the home state (Telangana) are intra-state, so the
    document should say "GST"; any other state is inter-state and should say
    "IGST". The percentage and amount calculation is unaffected — only the
    label changes.
    """
    if (state or "").strip().lower() == HOME_STATE:
        return "GST"
    return "IGST"


def compute_round_off(amount) -> tuple:
    """
    Round `amount` to the nearest whole rupee, matching Zoho's invoice/estimate
    "Round Off" behaviour.

    Returns (rounded_total, round_off) where round_off = rounded_total - amount,
    e.g. an amount of 2,97,224.10 rounds to 2,97,224.00 with round_off = -0.10.
    """
    amount = Decimal(str(amount))
    rounded = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return rounded, rounded - amount


def compute_order_grand_total(order) -> Decimal:
    """
    Grand total for an order's quotation, matching the figure printed on its
    estimate PDF (see EstimatePDFGenerator._build_estimate_info): per-item
    amount minus the order's discount%, plus each item's own GST%, then
    rounded to the nearest rupee. NQ (Not Quoted) items carry no price and
    are excluded, same as on the PDF.
    """
    discount_percentage = Decimal(str(order.discount_percentage or 0))
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for item in order.items:
        if item.is_nq or not item.unit_price:
            continue
        amount = Decimal(str(item.unit_price)) * item.quantity
        discount_amount = amount * (discount_percentage / 100)
        amount_after_discount = amount - discount_amount
        gst_percentage = Decimal(str(item.gst_percentage or 0))
        subtotal += amount
        total_tax += amount_after_discount * (gst_percentage / 100)

    discount_amount = subtotal * (discount_percentage / 100)
    subtotal_after_discount = subtotal - discount_amount
    grand_total, _round_off = compute_round_off(subtotal_after_discount + total_tax)
    return grand_total
