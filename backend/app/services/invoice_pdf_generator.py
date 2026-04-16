# invoice_pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from decimal import Decimal
import os
import math


# ---------- Register font with ₹ symbol ----------
def _register_unicode_font():
    """Register Unicode font for rupee symbol. Tries bundled font first, then system fonts."""
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up to backend/
    
    paths = [
        # Bundled font (highest priority)
        os.path.join(backend_dir, "fonts", "DejaVuSans.ttf"),
        # System fonts (fallback)
        "/Library/Fonts/DejaVuSans.ttf",
        "/Library/Fonts/DejaVu Sans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]
    
    for p in paths:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", p))
                return "DejaVuSans"
            except Exception:
                continue
    
    # Fallback to Helvetica (won't show ₹ symbol correctly)
    return "Helvetica"
_FONT = _register_unicode_font()
RUPEE = "₹"


# ---------- Helpers ----------
def format_indian_number(num):
    """Format number in Indian system (e.g., 12,34,567.89)."""
    try:
        num = float(num)
    except Exception:
        num = 0.0
    s = f"{num:,.2f}"
    parts = s.split(".")
    integer = parts[0].replace(",", "")
    if len(integer) <= 3:
        return s
    last_three = integer[-3:]
    remaining = integer[:-3]
    grouped = []
    while remaining:
        grouped.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    return ",".join(grouped) + "," + last_three + "." + parts[1]




# ---------- Invoice Generator ----------
class InvoicePDFGenerator:
    BRAND_COLOR = colors.HexColor("#1B4F72")
    ACCENT_COLOR = colors.HexColor("#DCECF8")

    def __init__(self, order, invoice, dispatch):
        from app.core.config import settings
        self.order = order
        self.invoice = invoice
        self.dispatch = dispatch
        self.settings = settings
        self.styles = getSampleStyleSheet()
        self._init_styles()

    # ---------- Styles ----------
    def _init_styles(self):
        self.styles.add(ParagraphStyle(
            name="CompanyName",
            fontSize=18, textColor=self.BRAND_COLOR,
            fontName=_FONT, leading=20
        ))
        self.styles.add(ParagraphStyle(
            name="InvoiceTitle",
            fontSize=18, textColor=self.BRAND_COLOR,
            fontName=_FONT, alignment=TA_CENTER, leading=20
        ))
        self.styles.add(ParagraphStyle(
            name="NormalText",
            fontSize=9, fontName=_FONT, leading=11
        ))
        self.styles.add(ParagraphStyle(
            name="RightText",
            fontSize=9, fontName=_FONT, alignment=TA_RIGHT, leading=11
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            fontSize=9, fontName=_FONT, textColor=colors.white,
            backColor=self.BRAND_COLOR, leftIndent=4, leading=11
        ))

    # ---------- Helper ----------
    def _fix_width(self, t):
        """Ensure consistent width across tables."""
        t._argW = [180 * mm] if len(t._argW) == 1 else t._argW
        return t

    # ---------- Header ----------
    def _header(self):
        # Get dynamic logo path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        logo_path = os.path.join(backend_dir, "uploads", "logo.png")
        logo = Image(logo_path, width=60 * mm, height=20 * mm) if os.path.exists(logo_path) else Paragraph("<b>Sreedevi Life Sciences</b>", self.styles["CompanyName"])
        info = (
            f"<b>{self.settings.COMPANY_NAME}</b><br/>"
            f"{self.settings.COMPANY_PLOT}, {self.settings.COMPANY_AREA}<br/>"
            f"{self.settings.COMPANY_CITY}, {self.settings.COMPANY_COUNTRY}<br/>"
            f"GSTIN: {self.settings.COMPANY_GSTIN}"
        )
        data = [[logo, Paragraph("<b>TAX INVOICE</b>", self.styles["InvoiceTitle"]), Paragraph(info, self.styles["RightText"])]]
        t = Table(data, colWidths=[65 * mm, 50 * mm, 65 * mm], rowHeights=[26 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ]))
        return t

    # ---------- Invoice Info ----------
    def _invoice_info(self):
        data = [
            ["Invoice No.", f": {self.invoice.invoice_number}", "Place Of Supply", f": {self.order.customer.state or 'N/A'}"],
            ["Invoice Date", f": {self.invoice.invoice_date.strftime('%d.%m.%Y')}", "Due Date", f": {self.invoice.due_date.strftime('%d.%m.%Y')}"]
        ]
        t = Table(data, colWidths=[30 * mm, 60 * mm, 40 * mm, 50 * mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return self._fix_width(t)

    # ---------- Bill To ----------
    def _bill_to(self):
        c = self.order.customer
        addr = f"<b>{c.hospital_name or c.name}</b><br/>{c.address or ''}<br/>{c.city or ''} - {c.pincode or ''}<br/>{c.state or ''}, India"
        data = [[Paragraph("Bill To", self.styles["SectionHeader"])],
                [Paragraph(addr, self.styles["NormalText"])]]
        t = Table(data, colWidths=[180 * mm])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return self._fix_width(t)

    # ---------- Items Table ----------
    def _items_table(self):
        headers = ["#", "Item & Description", "HSN/SAC", "Qty", "Rate", "IGST%", "IGST Amt", "Amount"]
        data = [headers]
        subtotal, total_igst = Decimal("0.00"), Decimal("0.00")
        num_cols = 8
        discount_percentage = float(getattr(self.order, 'discount_percentage', 0) or 0)

        # Group items by section_name
        sections_order = []
        sections_items = {}
        for item in self.dispatch.items:
            sec = getattr(item.order_item, 'section_name', None) or ''
            if sec not in sections_items:
                sections_items[sec] = []
                sections_order.append(sec)
            sections_items[sec].append(item)

        ordered_sections = [s for s in sections_order if s == ''] + [s for s in sections_order if s != '']
        has_named_sections = any(s != '' for s in ordered_sections)

        section_header_rows = []
        section_subtotal_rows = []
        i = 0

        for sec in ordered_sections:
            if sec:
                section_header_rows.append(len(data))
                data.append([Paragraph(f"<b>{sec}</b>", self.styles["SectionHeader"])] + [''] * (num_cols - 1))

            sec_subtotal = Decimal("0.00")
            for item in sections_items[sec]:
                i += 1
                rate = Decimal(item.order_item.unit_price or 0)
                qty = Decimal(item.quantity or 0)
                gst = Decimal(item.order_item.gst_percentage or 0)
                item_discount = rate * Decimal(str(discount_percentage / 100))
                discounted_rate = rate - item_discount
                amt = discounted_rate * qty
                igst = amt * gst / Decimal("100")
                sec_subtotal += amt
                subtotal += amt
                total_igst += igst
                data.append([
                    str(i),
                    Paragraph(f"<b>{item.inventory_item.sku}</b><br/>{item.inventory_item.description}", self.styles["NormalText"]),
                    item.inventory_item.hsn_code or "",
                    f"{qty}",
                    format_indian_number(discounted_rate),
                    f"{gst:.0f}%",
                    format_indian_number(igst),
                    format_indian_number(amt + igst)
                ])
            if has_named_sections and sec:
                section_subtotal_rows.append(len(data))
                data.append(["Sub Total"] + [''] * (num_cols - 2) + [format_indian_number(sec_subtotal)])

        if not has_named_sections:
            data.append(["Sub Total"] + [''] * (num_cols - 2) + [format_indian_number(subtotal)])

        grand = subtotal + total_igst
        igst_row = len(data)
        data.append(["IGST"] + [''] * (num_cols - 2) + [format_indian_number(total_igst)])
        data.append(["Grand Total"] + [''] * (num_cols - 2) + [f"{RUPEE}{format_indian_number(grand)}"])
        final_totals_rows = list(range(igst_row - (0 if has_named_sections else 1), len(data)))

        col_widths = [8*mm, 55*mm, 18*mm, 10*mm, 27*mm, 14*mm, 22*mm, 30*mm]
        t = Table(data, colWidths=col_widths)

        style = [
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), self.ACCENT_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ]

        for r in section_header_rows:
            style += [
                ("SPAN", (0, r), (num_cols - 1, r)),
                ("BACKGROUND", (0, r), (num_cols - 1, r), self.BRAND_COLOR),
                ("TEXTCOLOR", (0, r), (num_cols - 1, r), colors.white),
                ("FONTNAME", (0, r), (num_cols - 1, r), _FONT),
                ("LEFTPADDING", (0, r), (num_cols - 1, r), 4),
            ]

        for r in section_subtotal_rows + final_totals_rows:
            style += [
                ("SPAN", (0, r), (num_cols - 2, r)),
                ("ALIGN", (0, r), (num_cols - 2, r), "RIGHT"),
                ("FONTNAME", (0, r), (num_cols - 1, r), _FONT),
            ]

        t.setStyle(TableStyle(style))
        return self._fix_width(t)


    # ---------- Footer ----------
    def _footer(self):
        bank_text = (
            "<b>Bank Details</b><br/>"
            "Account Name : SREEDEVI LIFE SCIENCES<br/>"
            "Account Number : 50200079949944<br/>"
            "Bank Name : ICICI Bank<br/>"
            "IFSC Code : ICIC0007286<br/>"
            "Branch : ALKAPURI TOWNSHIP"
        )
        sign = Paragraph("<br/><br/>Authorized Signature", self.styles["RightText"])
        t = Table([[Paragraph(bank_text, self.styles["NormalText"]), sign]],
                  colWidths=[125*mm, 55*mm], rowHeights=[35*mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (0, 0), "TOP"),
            ("VALIGN", (1, 0), (1, 0), "BOTTOM"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return self._fix_width(t)

    # ---------- Terms ----------
    def _terms(self):
        terms = ("1) GST 12% is included in the Invoice.<br/>"
                 "2) Payment 100% in advance.<br/>"
                 "3) 3 years warranty.<br/>"
                 "4) Freight included.")
        data = [[Paragraph("Terms & Conditions", self.styles["SectionHeader"])],
                [Paragraph(terms, self.styles["NormalText"])]]
        t = Table(data, colWidths=[180 * mm])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return self._fix_width(t)

    # ---------- Build ----------
    def generate(self):
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        story = [
            self._header(), Spacer(1, 4*mm),
            self._invoice_info(), Spacer(1, 4*mm),
            self._bill_to(), Spacer(1, 5*mm),
            self._items_table(), Spacer(1, 6*mm),
            self._footer(), Spacer(1, 6*mm),
            self._terms(), Spacer(1, 6*mm),
            Paragraph("<font size=8 color='#666'><i>Sreedevi Life Sciences</i></font>",
                      self.styles["RightText"])
        ]
        doc.build(story)
        buf.seek(0)
        return buf


# ---------- Helper for FastAPI ----------
def generate_invoice_pdf(order, invoice, dispatch):
    generator = InvoicePDFGenerator(order, invoice, dispatch)
    return generator.generate()
