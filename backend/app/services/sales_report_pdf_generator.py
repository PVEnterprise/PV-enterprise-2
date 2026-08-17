"""
PDF generation for a sales rep's territory-scoped report summary.
One page: employee name, territories, period, and quotation/invoice totals.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from app.services.estimate_pdf_generator import RUPEE, format_indian_number, _FONT, _FONT_BOLD

BRAND_COLOR = colors.HexColor("#3d6b9e")
ACCENT_COLOR = colors.HexColor("#f4f7fb")


def generate_sales_report_pdf(
    sales_person_name: str,
    territory_names: list,
    period_label: str,
    period_start,
    period_end,
    quotations_count: int,
    quotations_value,
    invoices_count: int,
    invoices_value,
) -> BytesIO:
    from app.core.config import settings

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=18, textColor=BRAND_COLOR,
        fontName=_FONT_BOLD, alignment=TA_LEFT, leading=22,
    ))
    styles.add(ParagraphStyle(
        name="ReportNormal", fontSize=10, fontName=_FONT, alignment=TA_LEFT, leading=13,
    ))
    styles.add(ParagraphStyle(
        name="ReportSmall", fontSize=9, fontName=_FONT, alignment=TA_LEFT,
        leading=11, textColor=colors.HexColor("#64748b"),
    ))

    elements = [
        Paragraph(settings.COMPANY_NAME, styles["ReportSmall"]),
        Paragraph("Sales Report", styles["ReportTitle"]),
        Spacer(1, 4 * mm),
    ]

    info_data = [
        ["Sales Person", sales_person_name],
        ["Territory", ", ".join(territory_names) if territory_names else "— none assigned —"],
        ["Period", f"{period_label} ({period_start.strftime('%d %b %Y')} – {period_end.strftime('%d %b %Y')})"],
    ]
    info_table = Table(info_data, colWidths=[35 * mm, 130 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#334155")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8 * mm))

    metrics_data = [
        ["Metric", "Count", "Value"],
        ["Quotations", str(quotations_count), f"{RUPEE}{format_indian_number(float(quotations_value))}"],
        ["Invoices", str(invoices_count), f"{RUPEE}{format_indian_number(float(invoices_value))}"],
    ]
    metrics_table = Table(metrics_data, colWidths=[70 * mm, 40 * mm, 55 * mm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ACCENT_COLOR]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(metrics_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
