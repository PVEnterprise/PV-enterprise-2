"""
PDF generation for a sales rep's territory-scoped report summary.
One page, two-column body: Details (per-hospital breakdown) on the left,
Metrics (aggregate totals) on the right.
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
LEFT_COL_WIDTH = 108 * mm
RIGHT_COL_WIDTH = 58 * mm


def _money(value) -> str:
    return f"{RUPEE}{format_indian_number(float(value))}"


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
    hospitals: list,
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
        name="SectionHeading", fontSize=11, textColor=colors.HexColor("#1e293b"),
        fontName=_FONT_BOLD, alignment=TA_LEFT, leading=14,
    ))
    styles.add(ParagraphStyle(
        name="ReportSmall", fontSize=9, fontName=_FONT, alignment=TA_LEFT,
        leading=11, textColor=colors.HexColor("#64748b"),
    ))
    styles.add(ParagraphStyle(
        name="TableCell", fontSize=8, fontName=_FONT, alignment=TA_LEFT,
        leading=10, textColor=colors.HexColor("#1e293b"),
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
    info_table = Table(info_data, colWidths=[35 * mm, 131 * mm])
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

    # --- Left column: Details (per-hospital breakdown) ---
    left_flow = [Paragraph("Details", styles["SectionHeading"]), Spacer(1, 2 * mm)]
    if hospitals:
        hospital_data = [["Hospital", "Quotations", "Invoices"]]
        for h in hospitals:
            hospital_data.append([
                Paragraph(h.hospital_name, styles["TableCell"]),
                f"{h.quotations_count} / {_money(h.quotations_value)}" if h.quotations_count else "—",
                f"{h.invoices_count} / {_money(h.invoices_value)}" if h.invoices_count else "—",
            ])
        hospital_table = Table(hospital_data, colWidths=[48 * mm, 30 * mm, 30 * mm], repeatRows=1)
        hospital_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ACCENT_COLOR]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        left_flow.append(hospital_table)
    else:
        left_flow.append(Paragraph("No activity in this period.", styles["ReportSmall"]))

    # --- Right column: Metrics (aggregate totals) ---
    right_flow = [Paragraph("Metrics", styles["SectionHeading"]), Spacer(1, 2 * mm)]
    metrics_data = [
        ["Metric", "Count", "Value"],
        ["Quotations", str(quotations_count), _money(quotations_value)],
        ["Invoices", str(invoices_count), _money(invoices_value)],
    ]
    metrics_table = Table(metrics_data, colWidths=[22 * mm, 14 * mm, 22 * mm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ACCENT_COLOR]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    right_flow.append(metrics_table)

    columns_table = Table(
        [[left_flow, right_flow]],
        colWidths=[LEFT_COL_WIDTH, RIGHT_COL_WIDTH],
    )
    columns_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 6 * mm),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    elements.append(columns_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
