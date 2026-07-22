"""Tax label helpers for invoices and estimates/quotations."""

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
