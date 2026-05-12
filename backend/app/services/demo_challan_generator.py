"""
PDF generation service for Demo Challans.
Uses ReportLab to create professional demo challan PDFs in F1 style.
"""
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models.demo_request import DemoRequest


def _register_unicode_font():
    """Register NotoSans (regular + bold) for rupee symbol support."""
    try:
        pdfmetrics.getFont("NotoSans")
        pdfmetrics.getFont("NotoSans-Bold")
        return "NotoSans", "NotoSans-Bold"
    except KeyError:
        pass
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fonts")
    regular = os.path.normpath(os.path.join(fonts_dir, "NotoSans-Regular.ttf"))
    bold    = os.path.normpath(os.path.join(fonts_dir, "NotoSans-Bold.ttf"))
    if os.path.exists(regular):
        try:
            pdfmetrics.registerFont(TTFont("NotoSans", regular))
            pdfmetrics.registerFont(TTFont("NotoSans-Bold", bold if os.path.exists(bold) else regular))
            pdfmetrics.registerFontFamily(
                "NotoSans",
                normal="NotoSans", bold="NotoSans-Bold",
                italic="NotoSans", boldItalic="NotoSans-Bold",
            )
            return "NotoSans", "NotoSans-Bold"
        except Exception:
            pass
    return "Helvetica", "Helvetica-Bold"

_FONT, _FONT_BOLD = _register_unicode_font()


class DemoChallanPDFGenerator:
    """Generate professional demo challan PDFs in F1 style."""

    BRAND_COLOR = colors.HexColor("#3d6b9e")
    GREEN_COLOR = colors.HexColor("#56982c")
    ACCENT_COLOR = colors.HexColor("#f4f7fb")

    def __init__(self, demo_request: DemoRequest):
        from app.core.config import settings

        self.demo_request = demo_request
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        self.COMPANY_NAME = settings.COMPANY_NAME
        self.COMPANY_PLOT = settings.COMPANY_PLOT
        self.COMPANY_AREA = settings.COMPANY_AREA
        self.COMPANY_CITY = settings.COMPANY_CITY
        self.COMPANY_COUNTRY = settings.COMPANY_COUNTRY
        self.COMPANY_GSTIN = settings.COMPANY_GSTIN

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='ChallanTitle',
            fontSize=22,
            textColor=colors.HexColor('#56982c'),
            fontName=_FONT,
            alignment=TA_LEFT,
            leading=26,
            charSpace=4
        ))
        self.styles.add(ParagraphStyle(
            name='CompanyDetails',
            fontSize=9,
            fontName=_FONT,
            alignment=TA_RIGHT,
            leading=11
        ))
        self.styles.add(ParagraphStyle(
            name='NormalText',
            fontSize=9,
            fontName=_FONT,
            leading=11
        ))
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontSize=8,
            fontName=_FONT,
            leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='RightText',
            fontSize=9,
            fontName=_FONT,
            alignment=TA_RIGHT,
            leading=11
        ))

    def generate(self) -> BytesIO:
        """Generate the PDF and return as BytesIO buffer."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )

        story = []
        story.extend(self._build_header())
        story.extend(self._accent_bars())
        story.append(Spacer(1, 3*mm))
        story.extend(self._build_challan_info())
        story.append(Spacer(1, 3*mm))
        story.extend(self._build_ship_to())
        story.append(Spacer(1, 5*mm))
        story.extend(self._build_items_table())
        story.append(Spacer(1, 6*mm))
        story.extend(self._build_footer())
        story.append(Spacer(1, 5*mm))
        story.extend(self._build_terms())

        doc.build(story)
        self.buffer.seek(0)
        return self.buffer

    def _build_header(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        logo_path = os.path.join(backend_dir, "uploads", "logo.png")

        if os.path.exists(logo_path):
            try:
                logo_element = Image(logo_path, width=56*mm, height=22*mm)
            except Exception:
                logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['NormalText'])
        else:
            logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['NormalText'])

        title_block = Paragraph('<b>DEMO CHALLAN</b>', self.styles['ChallanTitle'])
        header_data = [[
            logo_element,
            '',
            title_block,
            Paragraph(
                f'{self.COMPANY_PLOT},<br/>'
                f'{self.COMPANY_AREA}, {self.COMPANY_CITY.split()[0]}<br/>'
                f"{' '.join(self.COMPANY_CITY.split()[1:])}, India<br/>"
                + '<font color="#3d6b9e"><b>'
                + ("" if self.COMPANY_GSTIN.upper().startswith("GSTIN") else "GSTIN: ")
                + self.COMPANY_GSTIN + '</b></font>',
                self.styles['CompanyDetails']
            )
        ]]
        t = Table(header_data, colWidths=[60*mm, 3*mm, 55*mm, 62*mm], rowHeights=[26*mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'LEFT'),
            ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 0),
            ('TOPPADDING', (0, 0), (0, 0), 0),
            ('BOTTOMPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 0),
            ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ('LINEBEFORE', (2, 0), (2, 0), 1.5, colors.HexColor('#d0dcea')),
        ]))
        return [t]

    def _accent_bars(self):
        b1 = Table([['']], colWidths=[180*mm], rowHeights=[4])
        b1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#56982c')),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        b2 = Table([['']], colWidths=[180*mm], rowHeights=[2])
        b2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#3d6b9e')),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return [b1, b2]

    def _build_challan_info(self):
        challan_date = self.demo_request.created_at.strftime('%d.%m.%Y')
        data = [
            ['Challan #', f': {self.demo_request.number}', 'Date', f': {challan_date}'],
        ]
        t = Table(data, colWidths=[30*mm, 60*mm, 30*mm, 60*mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _build_ship_to(self):
        dr = self.demo_request
        customer = getattr(dr, 'customer', None)
        if customer:
            name = getattr(customer, 'hospital_name', None) or getattr(customer, 'name', '') or ''
            addr = getattr(customer, 'address', '') or ''
            city = getattr(customer, 'city', '') or ''
            pincode = getattr(customer, 'pincode', '') or ''
            state = getattr(customer, 'state', '') or ''
            ship_text = f'<b>{name}</b><br/>{addr}<br/>{city} - {pincode}<br/>{state}, India'
        else:
            ship_text = getattr(dr, 'customer_name', '') or 'N/A'

        data = [
            [Paragraph('<font color="#3d6b9e"><b>SHIP TO</b></font>', self.styles['SmallText'])],
            [Paragraph(ship_text, self.styles['NormalText'])]
        ]
        t = Table(data, colWidths=[180*mm])
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f4f7fb')),
            ('LINEBEFORE', (0, 0), (0, -1), 2.5, colors.HexColor('#3d6b9e')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ]))
        return [t]

    def _build_items_table(self):
        cell_style = ParagraphStyle(
            'CellStyle', parent=self.styles['Normal'],
            fontSize=8, fontName=_FONT, leading=10
        )
        data = [['#', 'Catalog No', 'Item Description', 'Qty']]
        total_qty = 0
        for idx, item in enumerate(self.demo_request.items, 1):
            desc = Paragraph(
                f'<b>{item.inventory_item.sku}</b><br/>{item.inventory_item.description or ""}',
                cell_style
            )
            data.append([str(idx), item.inventory_item.sku, desc, str(item.quantity)])
            total_qty += item.quantity

        grand_row = len(data)
        data.append(['', '', Paragraph('<b>Total Items</b>', cell_style), str(total_qty)])

        t = Table(data, colWidths=[10*mm, 30*mm, 115*mm, 25*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), _FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, grand_row - 1), [colors.white, self.ACCENT_COLOR]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            # Bold quantity column for item rows
            ('FONTNAME', (3, 1), (3, grand_row - 1), _FONT_BOLD),
            ('BACKGROUND', (0, grand_row), (-1, grand_row), colors.HexColor('#3d6b9e')),
            ('TEXTCOLOR', (0, grand_row), (-1, grand_row), colors.white),
            ('FONTNAME', (0, grand_row), (-1, grand_row), _FONT_BOLD),
            ('FONTSIZE', (0, grand_row), (-1, grand_row), 9),
            ('TOPPADDING', (0, grand_row), (-1, grand_row), 5),
            ('BOTTOMPADDING', (0, grand_row), (-1, grand_row), 5),
            ('ALIGN', (2, grand_row), (2, grand_row), 'RIGHT'),
        ]))
        return [t]

    def _build_footer(self):
        sign = Paragraph('<br/><br/>Authorized Signature', self.styles['RightText'])
        note = Paragraph(
            '<b>Note:</b> Items are provided for demonstration purposes only. '
            'All items must be returned in good condition.',
            self.styles['SmallText']
        )
        t = Table([[note, sign]], colWidths=[125*mm, 55*mm], rowHeights=[35*mm])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('LINEABOVE', (0, 0), (-1, 0), 3, colors.HexColor('#56982c')),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return [t]

    def _build_terms(self):
        terms_text = (
            '1) All demo items must be returned within the agreed demo period.<br/>'
            '2) Any damage or loss of items will be charged at full price.<br/>'
            '3) Items are strictly for demonstration and evaluation purposes only.'
        )
        data = [
            [Paragraph('<font color="#3d6b9e"><b>TERMS &amp; CONDITIONS</b></font>', self.styles['SmallText'])],
            [Paragraph(terms_text, self.styles['NormalText'])]
        ]
        t = Table(data, colWidths=[180*mm])
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('LINEBEFORE', (0, 0), (0, 0), 2.5, colors.HexColor('#56982c')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ]))
        return [t]


def generate_demo_challan_pdf(demo_request: DemoRequest) -> BytesIO:
    """
    Generate a PDF demo challan for the given demo request.
    
    Args:
        demo_request: DemoRequest model instance with loaded relationships
        
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = DemoChallanPDFGenerator(demo_request)
    return generator.generate()
