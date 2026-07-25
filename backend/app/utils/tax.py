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
