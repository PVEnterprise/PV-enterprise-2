"""
PDF generation service for estimates/quotations.
Generates PDFs in Sreedevi Medtrade ESTIMATE format.
"""
import os
import math
from datetime import datetime, timedelta, date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models.order import Order
from app.models.customer import Customer


# ---------- Register font with ₹ symbol ----------
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
RUPEE = "₹"


def format_indian_number(num):
    """Format number in Indian numbering system (lakhs, crores)."""
    num_str = f"{num:.2f}"
    parts = num_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else '00'
    
    # Reverse the integer part for easier processing
    integer_part = integer_part[::-1]
    
    # First group of 3 digits, then groups of 2
    groups = []
    if len(integer_part) > 3:
        groups.append(integer_part[:3])
        integer_part = integer_part[3:]
        while integer_part:
            groups.append(integer_part[:2])
            integer_part = integer_part[2:]
    else:
        groups.append(integer_part)
    
    # Reverse back and join with commas
    formatted = ','.join(groups)[::-1]
    return f"{formatted}.{decimal_part}"




class EstimatePDFGenerator:
    """Generate ESTIMATE PDFs in Sreedevi Medtrade format."""
    
    # Brand Colors (F1 palette)
    BRAND_COLOR = colors.HexColor("#3d6b9e")
    GREEN_COLOR = colors.HexColor("#56982c")
    ACCENT_COLOR = colors.HexColor("#f4f7fb")
    
    # Bank Details
    BANK_ACCOUNT_NAME = "Sreedevi Life Sciences"
    BANK_ACCOUNT_NUMBER = "42285740549"
    BANK_NAME = "State Bank of India"
    BANK_IFSC = "SBIN0021790"
    BANK_BRANCH = "Manikonda, Hyderabad"
    
    DEFAULT_TERMS = (
        '1) Delivery within 10-12 weeks after receiving the confirmed Purchase Order and payment.\n'
        '2) Prices are mentioned in the Quote.\n'
        '3) Payment shall be made 100% in advance along with Purchase Order.\n'
        '4) 3 years warranty.\n'
        '5) Freight Included.'
    )

    def __init__(self, order: Order, expiry_date=None, bank_details: dict = None, quotation_number: int = None, terms_and_conditions: str = None):
        from app.core.config import settings
        
        self.order = order
        self.expiry_date = expiry_date
        self.customer: Customer = order.customer
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Load company info from settings
        self.COMPANY_NAME = settings.COMPANY_NAME
        self.COMPANY_PLOT = settings.COMPANY_PLOT
        self.COMPANY_AREA = settings.COMPANY_AREA
        self.COMPANY_CITY = settings.COMPANY_CITY
        self.COMPANY_COUNTRY = settings.COMPANY_COUNTRY
        self.COMPANY_GSTIN = settings.COMPANY_GSTIN
        
        # Override bank details if provided
        if bank_details:
            self.BANK_ACCOUNT_NAME = bank_details.get('bank_account_name', self.BANK_ACCOUNT_NAME)
            self.BANK_ACCOUNT_NUMBER = bank_details.get('bank_account_number', self.BANK_ACCOUNT_NUMBER)
            self.BANK_NAME = bank_details.get('bank_name', self.BANK_NAME)
            self.BANK_IFSC = bank_details.get('bank_ifsc', self.BANK_IFSC)
            self.BANK_BRANCH = bank_details.get('bank_branch', self.BANK_BRANCH)
        
        # Quotation number override (per-user auto-increment)
        self.quotation_number = quotation_number or getattr(order, 'quotation_number', None)
        
        # Terms and conditions override
        self.terms_and_conditions = terms_and_conditions or self.DEFAULT_TERMS
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontSize=18,
            textColor=self.BRAND_COLOR,
            fontName=_FONT,
            leading=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='EstimateTitle',
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
            name='RightText',
            fontSize=9,
            fontName=_FONT,
            alignment=TA_RIGHT,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=9,
            fontName=_FONT,
            textColor=colors.white,
            backColor=self.BRAND_COLOR,
            leftIndent=4,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionLabel',
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
        
        # Main content box with border
        content = []
        
        # Header with logo and company details
        content.extend(self._build_header())
        content.extend(self._accent_bars())
        content.append(Spacer(1, 3*mm))
        
        # Estimate info table
        content.extend(self._build_estimate_info())
        content.append(Spacer(1, 3*mm))
        
        # Bill To section
        content.extend(self._build_bill_to())
        content.append(Spacer(1, 3*mm))

        # Subject (optional)
        subject = getattr(self.order, 'subject', None)
        if subject:
            content.extend(self._build_subject(subject))
            content.append(Spacer(1, 3*mm))
        else:
            content.append(Spacer(1, 2*mm))
        
        # Items table
        content.extend(self._build_items_table())
        content.append(Spacer(1, 3*mm))
        
        # Bank details
        content.extend(self._build_bank_details())
        content.append(Spacer(1, 5*mm))
        
        # Terms and conditions
        content.extend(self._build_terms())
        
        story.extend(content)
        
        doc.build(story)
        self.buffer.seek(0)
        return self.buffer
    
    def _build_header(self):
        """Build header with logo and company details + ESTIMATE title."""
        elements = []
        
        # Get dynamic logo path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        logo_path = os.path.join(backend_dir, "uploads", "logo.png")
        logo_element = None
        
        if os.path.exists(logo_path):
            try:
                logo_element = Image(logo_path, width=56*mm, height=22*mm)
            except:
                # Fallback to text if logo fails
                logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        else:
            # Fallback to text placeholder
            logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        
        # Create header table: [Logo | ESTIMATE | Company Details]
        title_block = Paragraph('<b>ESTIMATE</b>', self.styles['EstimateTitle'])

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

        header_table = Table(header_data, colWidths=[60*mm, 3*mm, 55*mm, 62*mm], rowHeights=[26*mm])
        header_table.setStyle(TableStyle([
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
        
        elements.append(header_table)
        return elements
    
    def _accent_bars(self):
        """Two thin colored accent bars (F1 style)."""
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

    def _build_estimate_info(self):
        """Build estimate information table."""
        elements = []
        
        # Use quotation_number if set (per-user auto-increment), else fall back to order_number
        estimate_number = str(self.quotation_number) if self.quotation_number else self.order.order_number
        estimate_date = datetime.now().strftime('%d.%m.%Y')
        place_of_supply = self.customer.state or 'N/A'
        
        valid_until_str = self.expiry_date.strftime('%d.%m.%Y') if self.expiry_date else ''
        data = [
            ['#', f': {estimate_number}', 'Place Of Supply', f': {place_of_supply}'],
            ['Estimate Date', f': {estimate_date}', 'Valid Until' if valid_until_str else '', f': {valid_until_str}' if valid_until_str else '']
        ]
        
        table = Table(data, colWidths=[30*mm, 60*mm, 35*mm, 55*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_bill_to(self):
        """Build Bill To section."""
        elements = []
        
        # Build Bill To with section header
        customer_text = f'<b>{self.customer.hospital_name or self.customer.name}</b><br/>'
        if self.customer.address:
            customer_text += f'{self.customer.address}<br/>'
        if self.customer.city:
            customer_text += f'{self.customer.city}'
        if self.customer.pincode:
            customer_text += f' - {self.customer.pincode}'
        if self.customer.state:
            customer_text += f'<br/>{self.customer.state}, India'
        
        data = [
            [Paragraph('<font color="#3d6b9e"><b>BILL TO</b></font>', self.styles['SmallText'])],
            [Paragraph(customer_text, self.styles['NormalText'])]
        ]

        table = Table(data, colWidths=[180*mm])
        table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f4f7fb')),
            ('LINEBEFORE', (0, 0), (0, -1), 2.5, colors.HexColor('#3d6b9e')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ]))
        elements.append(table)
        
        return elements
    
    def _build_subject(self, subject: str):
        """Build Subject line shown below Bill To."""
        data = [[Paragraph(f'<b>Subject:</b> {subject}', self.styles['NormalText'])]]
        table = Table(data, colWidths=[180*mm])
        table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return [table]

    def _build_items_table(self):
        """Build items table grouped by section_name."""
        elements = []

        subtotal = Decimal('0.00')
        total_igst = Decimal('0.00')
        discount_percentage = float(getattr(self.order, 'discount_percentage', 0) or 0)
        show_discount_col = discount_percentage > 0
        num_cols = 10 if show_discount_col else 9

        if show_discount_col:
            header = [
                ['Sr No', 'Item Description', 'HSN/SAC', 'Unit Price', 'Qty', 'Discount\n%', 'Amount', 'IGST', '', 'Total'],
                ['', '', '', '', '', '', '', 'Tax%', 'Amt', '']
            ]
        else:
            header = [
                ['Sr No', 'Item Description', 'HSN/SAC', 'Unit Price', 'Qty', 'Amount', 'IGST', '', 'Total'],
                ['', '', '', '', '', '', 'Tax%', 'Amt', '']
            ]

        # Group decoded items by section_name
        decoded_items = [item for item in self.order.items if item.inventory_id]
        sections_order = []
        sections_items = {}
        for item in decoded_items:
            sec = getattr(item, 'section_name', None) or ''
            if sec not in sections_items:
                sections_items[sec] = []
                sections_order.append(sec)
            sections_items[sec].append(item)

        ordered_sections = [s for s in sections_order if s == ''] + [s for s in sections_order if s != '']
        has_named_sections = any(s != '' for s in ordered_sections)

        table_data = list(header)
        section_header_rows = []
        section_subtotal_rows = []
        idx = 0

        for sec in ordered_sections:
            if sec:
                section_header_rows.append(len(table_data))
                table_data.append([sec] + [''] * (num_cols - 1))

            sec_subtotal = Decimal('0.00')
            sec_igst = Decimal('0.00')
            for item in sections_items[sec]:
                idx += 1
                qty = item.quantity
                rate = float(item.unit_price or 0)
                amount = qty * rate
                igst_pct = float(item.gst_percentage or 0)
                item_discount = amount * (discount_percentage / 100)
                amount_after_discount = amount - item_discount
                igst_amt = amount_after_discount * (igst_pct / 100)
                total_amt = amount_after_discount + igst_amt
                sec_subtotal += Decimal(str(amount_after_discount))
                sec_igst += Decimal(str(igst_amt))
                subtotal += Decimal(str(amount))
                total_igst += Decimal(str(igst_amt))
                hsn_sac = item.inventory_item.hsn_code if hasattr(item.inventory_item, 'hsn_code') and item.inventory_item.hsn_code else ''
                if show_discount_col:
                    table_data.append([
                        str(idx),
                        Paragraph(f'<b>{item.inventory_item.sku}</b><br/>{item.inventory_item.description}', self.styles['SmallText']),
                        hsn_sac, format_indian_number(rate), f'{qty}',
                        f'{discount_percentage:.0f}%', format_indian_number(amount_after_discount),
                        f'{igst_pct:.0f}%', format_indian_number(igst_amt), format_indian_number(total_amt)
                    ])
                else:
                    table_data.append([
                        str(idx),
                        Paragraph(f'<b>{item.inventory_item.sku}</b><br/>{item.inventory_item.description}', self.styles['SmallText']),
                        hsn_sac, format_indian_number(rate), f'{qty}',
                        format_indian_number(amount_after_discount),
                        f'{igst_pct:.0f}%', format_indian_number(igst_amt), format_indian_number(total_amt)
                    ])

            if has_named_sections and sec:
                section_subtotal_rows.append(len(table_data))
                table_data.append([f'Sub Total — {sec}'] + [''] * (num_cols - 2) + [format_indian_number(float(sec_subtotal))])

        discount_amount = subtotal * (Decimal(str(discount_percentage)) / 100)
        subtotal_after_discount = subtotal - discount_amount
        grand_total = subtotal_after_discount + total_igst

        igst_label = f'IGST ({float(total_igst / subtotal_after_discount * 100) if subtotal_after_discount > 0 else 0:.0f}%)'
        final_rows_start = len(table_data)

        if not has_named_sections:
            table_data.append(['Sub Total'] + [''] * (num_cols - 2) + [format_indian_number(float(subtotal))])
            if discount_percentage > 0:
                table_data.append([f'Discount({discount_percentage:.2f}%)'] + [''] * (num_cols - 2) + [f'(-){format_indian_number(float(discount_amount))}'])
        table_data.append([igst_label] + [''] * (num_cols - 2) + [format_indian_number(float(total_igst))])
        table_data.append(['Total'] + [''] * (num_cols - 2) + [f'{RUPEE}{format_indian_number(float(grand_total))}'])

        if show_discount_col:
            colWidths = [8*mm, 42*mm, 15*mm, 16*mm, 10*mm, 12*mm, 19*mm, 13*mm, 19*mm, 26*mm]
        else:
            colWidths = [8*mm, 45*mm, 16*mm, 18*mm, 12*mm, 20*mm, 12*mm, 20*mm, 29*mm]

        table = Table(table_data, colWidths=colWidths)

        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 1), self.BRAND_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
            ('FONTNAME', (0, 0), (-1, 1), _FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTNAME', (0, -1), (-1, -1), _FONT_BOLD),
            # Bold + right-align value column for ALL data rows (items + summary + total)
            ('FONTNAME', (-1, 2), (-1, -1), _FONT_BOLD),
            ('ALIGN', (-1, 2), (-1, -1), 'RIGHT'),
        ]

        if show_discount_col:
            style_commands.extend([
                ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)), ('SPAN', (2, 0), (2, 1)),
                ('SPAN', (3, 0), (3, 1)), ('SPAN', (4, 0), (4, 1)), ('SPAN', (5, 0), (5, 1)),
                ('SPAN', (6, 0), (6, 1)), ('SPAN', (9, 0), (9, 1)), ('SPAN', (7, 0), (8, 0)),
            ])
        else:
            style_commands.extend([
                ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)), ('SPAN', (2, 0), (2, 1)),
                ('SPAN', (3, 0), (3, 1)), ('SPAN', (4, 0), (4, 1)), ('SPAN', (5, 0), (5, 1)),
                ('SPAN', (8, 0), (8, 1)), ('SPAN', (6, 0), (7, 0)),
            ])

        # Section header rows (dark blue background)
        for r in section_header_rows:
            style_commands.extend([
                ('SPAN', (0, r), (num_cols - 1, r)),
                ('BACKGROUND', (0, r), (num_cols - 1, r), self.BRAND_COLOR),
                ('TEXTCOLOR', (0, r), (num_cols - 1, r), colors.white),
                ('FONTNAME', (0, r), (num_cols - 1, r), _FONT_BOLD),
                ('ALIGN', (0, r), (num_cols - 1, r), 'LEFT'),
            ])

        # Section subtotal rows + final totals rows: merge all except last col
        for r in section_subtotal_rows + list(range(final_rows_start, len(table_data) - 1)):
            style_commands.extend([
                ('SPAN', (0, r), (num_cols - 2, r)),
                ('ALIGN', (0, r), (0, r), 'RIGHT'),
                ('ALIGN', (num_cols - 1, r), (num_cols - 1, r), 'RIGHT'),
                ('FONTNAME', (0, r), (num_cols - 1, r), _FONT_BOLD),
                ('BACKGROUND', (0, r), (-1, r), colors.HexColor('#eef2f7')),
            ])
        grand_row = len(table_data) - 1
        style_commands.extend([
            ('SPAN', (0, grand_row), (num_cols - 2, grand_row)),
            ('ALIGN', (0, grand_row), (0, grand_row), 'RIGHT'),
            ('ALIGN', (num_cols - 1, grand_row), (num_cols - 1, grand_row), 'RIGHT'),
            ('BACKGROUND', (0, grand_row), (-1, grand_row), colors.HexColor('#3d6b9e')),
            ('TEXTCOLOR', (0, grand_row), (-1, grand_row), colors.white),
            ('FONTNAME', (0, grand_row), (-1, grand_row), _FONT_BOLD),
            ('FONTSIZE', (0, grand_row), (-1, grand_row), 9),
            ('TOPPADDING', (0, grand_row), (-1, grand_row), 5),
            ('BOTTOMPADDING', (0, grand_row), (-1, grand_row), 5),
        ])

        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        return elements
    
    
    def _build_bank_details(self):
        """Build bank details section."""
        elements = []
        
        bank_text = (
            f'<b>Bank Details</b><br/>'
            f'Account Name : {self.BANK_ACCOUNT_NAME}<br/>'
            f'Account Number : {self.BANK_ACCOUNT_NUMBER}<br/>'
            f'Bank Name : {self.BANK_NAME}<br/>'
            f'Bank IFSC Code : {self.BANK_IFSC}<br/>'
            f'Branch Name : {self.BANK_BRANCH}'
        )
        
        signature_text = '<br/><br/>Authorized Signature'
        
        data = [[
            Paragraph(bank_text, self.styles['SmallText']),
            Paragraph(signature_text, self.styles['NormalText'])
        ]]
        
        table = Table(data, colWidths=[125*mm, 55*mm], rowHeights=[35*mm])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('LINEABOVE', (0, 0), (-1, 0), 3, colors.HexColor('#56982c')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_terms(self):
        """Build terms and conditions section."""
        elements = []
        
        terms_text = self.terms_and_conditions.replace('\n', '<br/>')
        
        data = [
            [Paragraph('<font color="#3d6b9e"><b>TERMS &amp; CONDITIONS</b></font>', self.styles['SmallText'])],
            [Paragraph(terms_text, self.styles['NormalText'])]
        ]

        table = Table(data, colWidths=[180*mm])
        table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.HexColor('#d0dcea')),
            ('LINEBEFORE', (0, 0), (0, 0), 2.5, colors.HexColor('#56982c')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ]))
        
        elements.append(table)
        return elements



def generate_estimate_pdf(order: Order, expiry_date=None, bank_details: dict = None, quotation_number: int = None, terms_and_conditions: str = None) -> BytesIO:
    """
    Generate an ESTIMATE PDF for the given order.

    Args:
        order: Order model instance with loaded relationships (customer, items, inventory)
        expiry_date: Optional date object for quotation validity
        bank_details: Optional dict with bank account details to override defaults
        quotation_number: Optional int to override the displayed quotation number
        terms_and_conditions: Optional string to override the default T&C text

    Returns:
        BytesIO buffer containing the PDF
    """
    generator = EstimatePDFGenerator(order, expiry_date=expiry_date, bank_details=bank_details, quotation_number=quotation_number, terms_and_conditions=terms_and_conditions)
    return generator.generate()
