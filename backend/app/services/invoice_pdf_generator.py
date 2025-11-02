"""
Invoice PDF Generator Service.
Generates TAX INVOICE PDFs for dispatched orders.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
from decimal import Decimal
from datetime import datetime
import os


def format_indian_number(num):
    """Format number in Indian numbering system (lakhs, crores)."""
    s = f"{num:,.2f}"
    # Convert western format (1,234,567.89) to Indian format (12,34,567.89)
    parts = s.split('.')
    integer_part = parts[0].replace(',', '')
    
    if len(integer_part) <= 3:
        return s
    
    # Indian grouping: last 3 digits, then groups of 2
    last_three = integer_part[-3:]
    remaining = integer_part[:-3]
    
    # Group remaining digits in pairs from right to left
    grouped = []
    while remaining:
        grouped.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    
    result = ','.join(grouped) + ',' + last_three if grouped else last_three
    return result + '.' + parts[1]


def number_to_words_indian_rupees(num):
    """Convert number to Indian Rupees in words."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    
    def convert_below_hundred(n):
        if n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        else:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
    
    def convert_below_thousand(n):
        if n < 100:
            return convert_below_hundred(n)
        else:
            return ones[n // 100] + ' Hundred' + (' ' + convert_below_hundred(n % 100) if n % 100 != 0 else '')
    
    if num == 0:
        return 'Zero Rupees Only'
    
    # Split into rupees and paise
    rupees = int(num)
    paise = int(round((num - rupees) * 100))
    
    result = []
    
    # Crores
    if rupees >= 10000000:
        crores = rupees // 10000000
        result.append(convert_below_thousand(crores) + ' Crore')
        rupees %= 10000000
    
    # Lakhs
    if rupees >= 100000:
        lakhs = rupees // 100000
        result.append(convert_below_thousand(lakhs) + ' Lakh')
        rupees %= 100000
    
    # Thousands
    if rupees >= 1000:
        thousands = rupees // 1000
        result.append(convert_below_thousand(thousands) + ' Thousand')
        rupees %= 1000
    
    # Hundreds and below
    if rupees > 0:
        result.append(convert_below_thousand(rupees))
    
    words = ' '.join(result) + ' Rupees'
    
    if paise > 0:
        words += ' and ' + convert_below_hundred(paise) + ' Paise'
    
    return words + ' Only'


class InvoicePDFGenerator:
    """Generate TAX INVOICE PDF from order and dispatch data."""
    
    # Bank details
    BANK_NAME = "ICICI Bank"
    BANK_ACCOUNT_NAME = "SREEDEVI MEDTRADE"
    BANK_ACCOUNT_NUMBER = "50200079949944"
    BANK_IFSC = "ICIC0007286"
    BANK_BRANCH = "ALKAPURI TOWNSHIP"
    
    def __init__(self, order, invoice, dispatch):
        """Initialize with order, invoice, and dispatch data."""
        from app.core.config import settings
        
        self.order = order
        self.invoice = invoice
        self.dispatch = dispatch
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Load company info from settings
        self.COMPANY_NAME = settings.COMPANY_NAME
        self.COMPANY_PLOT = settings.COMPANY_PLOT
        self.COMPANY_AREA = settings.COMPANY_AREA
        self.COMPANY_CITY = settings.COMPANY_CITY
        self.COMPANY_COUNTRY = settings.COMPANY_COUNTRY
        self.COMPANY_GSTIN = settings.COMPANY_GSTIN
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2C5F2D'),
            spaceAfter=2
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyDetails',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=TA_RIGHT,
            textColor=colors.black
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=7,
            leading=9
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        ))
    
    def _build_header(self):
        """Build header with logo and company details + TAX INVOICE title."""
        elements = []
        
        # Try to load logo
        logo_path = '/Users/praneeth/Documents/PV_enterprise_2/backend/uploads/logo.png'
        logo_element = None
        
        if os.path.exists(logo_path):
            try:
                logo_element = Image(logo_path, width=65*mm, height=22*mm)
            except:
                logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        else:
            logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        
        # Create header table: [Logo | TAX INVOICE | Company Details]
        header_data = [[
            logo_element,
            Paragraph('<b>TAX INVOICE</b>', self.styles['InvoiceTitle']),
            Paragraph(
                f'<b>{self.COMPANY_NAME}</b><br/>'
                f'{self.COMPANY_PLOT}<br/>'
                f'{self.COMPANY_AREA}<br/>'
                f'{self.COMPANY_CITY}<br/>'
                f'{self.COMPANY_COUNTRY}<br/>'
                f'{self.COMPANY_GSTIN}',
                self.styles['CompanyDetails']
            )
        ]]
        
        header_table = Table(header_data, colWidths=[70*mm, 45*mm, 65*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        return elements
    
    def _build_invoice_info(self):
        """Build invoice information section."""
        elements = []
        
        # Invoice info table
        invoice_data = [
            ['#', f': {self.invoice.invoice_number}', 'Place Of Supply', f': {self.order.customer.state or "N/A"}'],
            ['Invoice Date', f': {self.invoice.invoice_date.strftime("%d.%m.%Y")}', '', ''],
            ['Terms', f': {self.invoice.payment_terms or "Net0"}', '', ''],
            ['Due Date', f': {self.invoice.due_date.strftime("%d.%m.%Y")}', '', ''],
        ]
        
        info_table = Table(invoice_data, colWidths=[30*mm, 60*mm, 45*mm, 45*mm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(info_table)
        return elements
    
    def _build_bill_to(self):
        """Build Bill To section."""
        elements = []
        
        customer = self.order.customer
        address_parts = [customer.hospital_name or customer.name]
        if customer.address:
            address_parts.append(customer.address)
        if customer.city or customer.state or customer.pincode:
            city_state_parts = []
            if customer.city:
                city_state_parts.append(customer.city)
            if customer.pincode:
                city_state_parts.append(customer.pincode)
            if customer.state:
                city_state_parts.append(customer.state)
            address_parts.append(' '.join(city_state_parts))
        address_parts.append('India')
        
        bill_to_data = [
            ['Bill To'],
            ['\n'.join(address_parts)]
        ]
        
        bill_to_table = Table(bill_to_data, colWidths=[180*mm])
        bill_to_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(bill_to_table)
        return elements
    
    def _build_items_table(self):
        """Build items table with dispatched quantities."""
        elements = []
        
        # Calculate totals
        subtotal = Decimal('0.00')
        total_igst = Decimal('0.00')
        
        # Get discount from order
        discount_percentage = float(getattr(self.order, 'discount_percentage', 0) or 0)
        
        # Header - Simple structure for invoice
        # Columns: Sr No, Item Description, HSN/SAC, Qty, Rate, IGST (%, Amt), Amount
        header = [
            ['#', 'Item & Description', 'HSN/SAC', 'Qty', 'Rate', 'IGST', '', 'Amount'],
            ['', '', '', '', '', '%', 'Amt', '']
        ]
        
        # Items - use dispatch items
        items_data = []
        for idx, dispatch_item in enumerate(self.dispatch.items, 1):
            order_item = dispatch_item.order_item
            inventory = dispatch_item.inventory_item
            
            qty = dispatch_item.quantity  # Dispatched quantity
            
            # Use order_item.unit_price (this is the price list price, e.g., Apollo price)
            # Then apply the discount from order level
            rate = float(order_item.unit_price or 0)
            
            # Apply discount to get the final rate (same logic as estimate PDF)
            item_discount = rate * (discount_percentage / 100)
            discounted_rate = rate - item_discount
            
            amount = qty * discounted_rate
            igst_pct = float(order_item.gst_percentage or 0)
            igst_amt = amount * (igst_pct / 100)
            total_amt = amount + igst_amt
            
            subtotal += Decimal(str(amount))
            total_igst += Decimal(str(igst_amt))
            
            # Get HSN/SAC
            hsn_sac = inventory.hsn_code if hasattr(inventory, 'hsn_code') and inventory.hsn_code else ''
            
            items_data.append([
                str(idx),
                Paragraph(f'<b>{inventory.sku}</b><br/>{inventory.description}', self.styles['SmallText']),
                hsn_sac,
                f'{qty}',
                format_indian_number(discounted_rate),
                f'{igst_pct:.0f}%',
                format_indian_number(igst_amt),
                format_indian_number(total_amt)
            ])
        
        # Combine header and items
        table_data = header + items_data
        
        # Add totals rows
        grand_total = subtotal + total_igst
        
        # Totals rows - merge columns 0-6, amount in column 7
        table_data.append(['Sub Total', '', '', '', '', '', '', format_indian_number(float(subtotal))])
        table_data.append([f'IGST5 ({float(total_igst/subtotal*100) if subtotal > 0 else 0:.0f}%)', '', '', '', '', '', '', format_indian_number(float(total_igst))])
        table_data.append(['Total', '', '', '', '', '', '', f'Rs.{format_indian_number(float(grand_total))}'])
        table_data.append(['Balance Due', '', '', '', '', '', '', f'Rs.{format_indian_number(float(grand_total))}'])
        
        # Calculate number of item rows
        num_items = len(items_data)
        totals_start_row = 2 + num_items
        
        # Column widths: #, Item&Desc, HSN/SAC, Qty, Rate, IGST%, IGST Amt, Amount
        # Total: 8+50+18+15+20+12+20+37 = 180mm
        table = Table(table_data, colWidths=[8*mm, 50*mm, 18*mm, 15*mm, 20*mm, 12*mm, 20*mm, 37*mm])
        
        # Build style
        style_commands = [
            # Header rows (2 rows)
            ('BACKGROUND', (0, 0), (-1, 1), colors.white),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 1), 8),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('GRID', (0, 0), (-1, 1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'),
            
            # Merge columns vertically for all except IGST (5-6)
            ('SPAN', (0, 0), (0, 1)),  # #
            ('SPAN', (1, 0), (1, 1)),  # Item & Description
            ('SPAN', (2, 0), (2, 1)),  # HSN/SAC
            ('SPAN', (3, 0), (3, 1)),  # Qty
            ('SPAN', (4, 0), (4, 1)),  # Rate
            ('SPAN', (7, 0), (7, 1)),  # Amount
            ('SPAN', (5, 0), (6, 0)),  # IGST parent header
            
            # Data rows
            ('FONTSIZE', (0, 2), (-1, num_items + 1), 8),
            ('ALIGN', (0, 2), (0, num_items + 1), 'CENTER'),  # #
            ('ALIGN', (1, 2), (1, num_items + 1), 'LEFT'),    # Description
            ('ALIGN', (2, 2), (2, num_items + 1), 'CENTER'),  # HSN/SAC
            ('ALIGN', (3, 2), (-1, num_items + 1), 'RIGHT'),  # Rest right-aligned
            ('GRID', (0, 2), (-1, num_items + 1), 0.5, colors.black),
            ('VALIGN', (0, 2), (-1, num_items + 1), 'TOP'),
            
            # Totals rows
            ('FONTSIZE', (0, totals_start_row), (-1, -1), 8),
            ('ALIGN', (0, totals_start_row), (-1, -1), 'RIGHT'),
            ('GRID', (0, totals_start_row), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, totals_start_row), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Total row bold
            ('FONTNAME', (0, -2), (-1, -2), 'Helvetica-Bold'),  # Balance Due row bold
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        
        # Add span commands for totals rows
        for i in range(totals_start_row, len(table_data)):
            style_commands.append(('SPAN', (0, i), (6, i)))
        
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        return elements
    
    def _build_total_in_words(self):
        """Build total in words section."""
        elements = []
        
        total = float(self.invoice.total_amount or 0)
        words = number_to_words_indian_rupees(total)
        
        words_data = [
            ['Total In Words'],
            [Paragraph(f'<i>{words}</i>', self.styles['NormalText'])]
        ]
        
        words_table = Table(words_data, colWidths=[180*mm])
        words_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(words_table)
        return elements
    
    def _build_bank_and_signature(self):
        """Build bank details and authorized signature section."""
        elements = []
        
        # Bank details
        bank_details = (
            f"<b>Bank Details</b><br/>"
            f"Account Name : {self.BANK_ACCOUNT_NAME}<br/>"
            f"Account Number : {self.BANK_ACCOUNT_NUMBER}<br/>"
            f"Bank Name : {self.BANK_NAME}<br/>"
            f"Bank IFSC Code : {self.BANK_IFSC}<br/>"
            f"Branch Name : {self.BANK_BRANCH}"
        )
        
        # Authorized signature
        auth_sig = "Authorized Signature"
        
        combined_data = [
            [
                Paragraph(bank_details, self.styles['NormalText']),
                Paragraph(auth_sig, self.styles['NormalText'])
            ]
        ]
        
        combined_table = Table(combined_data, colWidths=[140*mm, 40*mm])
        combined_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(combined_table)
        return elements
    
    def _build_terms(self):
        """Build terms and conditions section."""
        elements = []
        
        terms_text = (
            "1)GST 12% is included in the Invoice.<br/>"
            "3)Payment shall be made 100% in advance along side with Delivery.<br/>"
            "4)3 years warranty.<br/>"
            "5)Freight included."
        )
        
        terms_data = [
            ['Terms & Conditions'],
            [Paragraph(terms_text, self.styles['NormalText'])]
        ]
        
        terms_table = Table(terms_data, colWidths=[180*mm])
        terms_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(terms_table)
        return elements
    
    def generate(self):
        """Generate the complete invoice PDF."""
        buffer = BytesIO()
        
        # Create PDF with margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        # Build document elements
        story = []
        
        # Header
        story.extend(self._build_header())
        story.append(Spacer(1, 3*mm))
        
        # Invoice info
        story.extend(self._build_invoice_info())
        story.append(Spacer(1, 3*mm))
        
        # Bill To
        story.extend(self._build_bill_to())
        story.append(Spacer(1, 3*mm))
        
        # Items table
        story.extend(self._build_items_table())
        story.append(Spacer(1, 3*mm))
        
        # Total in words
        story.extend(self._build_total_in_words())
        story.append(Spacer(1, 3*mm))
        
        # Bank details and signature
        story.extend(self._build_bank_and_signature())
        story.append(Spacer(1, 3*mm))
        
        # Terms
        story.extend(self._build_terms())
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer


def generate_invoice_pdf(order, invoice, dispatch):
    """Helper function to generate invoice PDF."""
    generator = InvoicePDFGenerator(order, invoice, dispatch)
    return generator.generate()
