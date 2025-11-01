"""
PDF generation service for estimates/quotations.
Generates PDFs in Sreedevi Medtrade ESTIMATE format.
"""
import os
from datetime import datetime, timedelta, date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from app.models.order import Order
from app.models.customer import Customer


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


def number_to_words(num):
    """Convert number to Indian Rupees words."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    
    def convert_below_thousand(n):
        if n == 0:
            return ''
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
        else:
            return ones[n // 100] + ' Hundred' + (' ' + convert_below_thousand(n % 100) if n % 100 != 0 else '')
    
    if num == 0:
        return 'Zero'
    
    # Handle decimals
    num = int(num)
    
    crore = num // 10000000
    num %= 10000000
    lakh = num // 100000
    num %= 100000
    thousand = num // 1000
    num %= 1000
    
    result = []
    if crore:
        result.append(convert_below_thousand(crore) + ' Crore')
    if lakh:
        result.append(convert_below_thousand(lakh) + ' Lakh')
    if thousand:
        result.append(convert_below_thousand(thousand) + ' Thousand')
    if num:
        result.append(convert_below_thousand(num))
    
    return ' '.join(result)


class EstimatePDFGenerator:
    """Generate ESTIMATE PDFs in Sreedevi Medtrade format."""
    
    # Company Information
    COMPANY_NAME = "Sreedevi Medtrade"
    COMPANY_PLOT = "Plot No: 173 Road No: 14"
    COMPANY_AREA = "Alkapuri Township"
    COMPANY_CITY = "Hyderabad Telangana 500089"
    COMPANY_COUNTRY = "India"
    COMPANY_GSTIN = "GSTIN 36AABCS2596E1Z8"
    
    # Bank Details
    BANK_ACCOUNT_NAME = "SREEDEVI MEDTRADE"
    BANK_ACCOUNT_NUMBER = "50200079949944"
    BANK_NAME = "ICICI Bank"
    BANK_IFSC = "ICIC0007286"
    BANK_BRANCH = "ALKAPURI TOWNSHIP"
    
    def __init__(self, order: Order):
        self.order = order
        self.customer: Customer = order.customer
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=16,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
            spaceAfter=2
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyDetails',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='EstimateTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT,
            spaceAfter=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            spaceAfter=3
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
            fontSize=8,
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
        content.append(Spacer(1, 3*mm))
        
        # Estimate info table
        content.extend(self._build_estimate_info())
        content.append(Spacer(1, 3*mm))
        
        # Bill To section
        content.extend(self._build_bill_to())
        content.append(Spacer(1, 5*mm))
        
        # Items table
        content.extend(self._build_items_table())
        content.append(Spacer(1, 3*mm))
        
        # Total in words
        content.extend(self._build_total_in_words())
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
        
        # Try to load logo from attachments
        logo_path = '/Users/praneeth/Documents/PV_enterprise_2/backend/uploads/logo.png'
        logo_element = None
        
        if os.path.exists(logo_path):
            try:
                logo_element = Image(logo_path, width=65*mm, height=22*mm)
            except:
                # Fallback to text if logo fails
                logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        else:
            # Fallback to text placeholder
            logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        
        # Create header table: [Logo | Company Details | ESTIMATE]
        header_data = [[
            logo_element,
            Paragraph(
                f'<b>{self.COMPANY_NAME}</b><br/>'
                f'{self.COMPANY_PLOT}<br/>'
                f'{self.COMPANY_AREA}<br/>'
                f'{self.COMPANY_CITY}<br/>'
                f'{self.COMPANY_COUNTRY}<br/>'
                f'{self.COMPANY_GSTIN}',
                self.styles['CompanyDetails']
            ),
            Paragraph('<b>ESTIMATE</b>', self.styles['EstimateTitle'])
        ]]
        
        # Adjust column widths: wider logo column to prevent company info overlap
        header_table = Table(header_data, colWidths=[70*mm, 65*mm, 45*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        return elements
    
    def _build_estimate_info(self):
        """Build estimate information table."""
        elements = []
        
        # Use order number for #
        estimate_number = self.order.order_number
        estimate_date = datetime.now().strftime('%d.%m.%Y')
        place_of_supply = "Maharashtra (27)"  # Default, should come from customer state
        
        data = [
            ['#', f': {estimate_number}', 'Place Of Supply', f': {place_of_supply}'],
            ['Estimate Date', f': {estimate_date}', '', '']
        ]
        
        table = Table(data, colWidths=[30*mm, 60*mm, 35*mm, 55*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_bill_to(self):
        """Build Bill To section."""
        elements = []
        
        # Bill To label
        bill_to_label = [[Paragraph('<b>Bill To</b>', self.styles['SectionLabel'])]]
        label_table = Table(bill_to_label, colWidths=[180*mm])
        label_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(label_table)
        
        # Customer details
        customer_text = f'<b>{self.customer.hospital_name or self.customer.name}</b><br/>'
        if self.customer.address:
            customer_text += f'{self.customer.address}<br/>'
        if self.customer.city:
            customer_text += f'{self.customer.city}'
        if self.customer.pincode:
            customer_text += f' {self.customer.pincode}'
        if self.customer.state:
            customer_text += f' {self.customer.state}'
        if self.customer.city or self.customer.pincode or self.customer.state:
            customer_text += '<br/>'
        customer_text += 'India'
        
        customer_data = [[Paragraph(customer_text, self.styles['NormalText'])]]
        customer_table = Table(customer_data, colWidths=[180*mm])
        customer_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(customer_table)
        
        return elements
    
    def _build_items_table(self):
        """Build items table."""
        elements = []
        
        # Calculate totals
        subtotal = Decimal('0.00')
        total_igst = Decimal('0.00')
        
        # Get discount from order first to calculate tax correctly
        discount_percentage = float(getattr(self.order, 'discount_percentage', 0) or 0)
        
        # Header - New structure with Discount% column
        # Columns: Sr No, Item Description, HSN/SAC, Unit Price, Qty, Discount%, Amount, IGST (Tax%, Amt), Total
        # Show Discount% column only if discount > 0
        show_discount_col = discount_percentage > 0
        
        if show_discount_col:
            header = [
                ['Sr No', 'Item Description', 'HSN/SAC', 'Unit Price', 'Qty', 'Discount%', 'Amount', 'IGST', '', 'Total'],
                ['', '', '', '', '', '', '', 'Tax%', 'Amt', '']
            ]
        else:
            header = [
                ['Sr No', 'Item Description', 'HSN/SAC', 'Unit Price', 'Qty', 'Amount', 'IGST', '', 'Total'],
                ['', '', '', '', '', '', 'Tax%', 'Amt', '']
            ]
        
        # Items
        items_data = []
        for idx, item in enumerate(self.order.items, 1):
            if not item.inventory_id:
                continue  # Skip non-decoded items
            
            qty = item.quantity
            rate = float(item.unit_price or 0)
            amount = qty * rate
            igst_pct = float(item.gst_percentage or 0)
            
            # Apply discount to item amount first, then calculate tax
            item_discount = amount * (discount_percentage / 100)
            amount_after_discount = amount - item_discount
            igst_amt = amount_after_discount * (igst_pct / 100)
            total_amt = amount_after_discount + igst_amt
            
            subtotal += Decimal(str(amount))
            total_igst += Decimal(str(igst_amt))
            
            # Get HSN/SAC from inventory
            hsn_sac = item.inventory_item.hsn_code if hasattr(item.inventory_item, 'hsn_code') and item.inventory_item.hsn_code else ''
            
            # Build row based on whether discount column is shown
            if show_discount_col:
                items_data.append([
                    str(idx),  # Sr No
                    Paragraph(f'<b>{item.inventory_item.sku}</b><br/>{item.inventory_item.description}', self.styles['SmallText']),  # Item Description
                    hsn_sac,  # HSN/SAC
                    format_indian_number(rate),  # Unit Price
                    f'{qty}',  # Qty
                    f'{discount_percentage:.0f}%',  # Discount%
                    format_indian_number(amount_after_discount),  # Amount (after discount)
                    f'{igst_pct:.0f}%',  # IGST Tax%
                    format_indian_number(igst_amt),  # IGST Amt
                    format_indian_number(total_amt)  # Total
                ])
            else:
                items_data.append([
                    str(idx),  # Sr No
                    Paragraph(f'<b>{item.inventory_item.sku}</b><br/>{item.inventory_item.description}', self.styles['SmallText']),  # Item Description
                    hsn_sac,  # HSN/SAC
                    format_indian_number(rate),  # Unit Price
                    f'{qty}',  # Qty
                    format_indian_number(amount_after_discount),  # Amount (after discount)
                    f'{igst_pct:.0f}%',  # IGST Tax%
                    format_indian_number(igst_amt),  # IGST Amt
                    format_indian_number(total_amt)  # Total
                ])
        
        # Combine header and items
        table_data = header + items_data
        
        # Add totals rows with discount
        discount_amount = subtotal * (Decimal(str(discount_percentage)) / 100)
        subtotal_after_discount = subtotal - discount_amount
        rounding = Decimal('0.00')  # Can be calculated if needed
        grand_total = subtotal_after_discount + total_igst + rounding
        
        # Totals rows - adjust based on whether discount column is shown
        num_cols = 10 if show_discount_col else 9
        merge_to_col = num_cols - 2  # Merge all columns except last one
        
        # Build totals rows
        if show_discount_col:
            table_data.append(['Sub Total'] + [''] * (num_cols - 2) + [format_indian_number(float(subtotal))])
            if discount_percentage > 0:
                table_data.append([f'Discount({discount_percentage:.2f}%)'] + [''] * (num_cols - 2) + [f'(-){format_indian_number(float(discount_amount))}'])
            table_data.append([f'IGST ({float(total_igst/subtotal*100) if subtotal > 0 else 0:.0f}%)'] + [''] * (num_cols - 2) + [format_indian_number(float(total_igst))])
            if rounding != 0:
                table_data.append(['Rounding'] + [''] * (num_cols - 2) + [format_indian_number(float(rounding))])
            table_data.append(['Total'] + [''] * (num_cols - 2) + [f'Rs.{format_indian_number(float(grand_total))}'])
        else:
            table_data.append(['Sub Total'] + [''] * (num_cols - 2) + [format_indian_number(float(subtotal))])
            if discount_percentage > 0:
                table_data.append([f'Discount({discount_percentage:.2f}%)'] + [''] * (num_cols - 2) + [f'(-){format_indian_number(float(discount_amount))}'])
            table_data.append([f'IGST ({float(total_igst/subtotal*100) if subtotal > 0 else 0:.0f}%)'] + [''] * (num_cols - 2) + [format_indian_number(float(total_igst))])
            if rounding != 0:
                table_data.append(['Rounding'] + [''] * (num_cols - 2) + [format_indian_number(float(rounding))])
            table_data.append(['Total'] + [''] * (num_cols - 2) + [f'Rs.{format_indian_number(float(grand_total))}'])
        
        # Calculate number of item rows (total rows - 2 header rows - totals rows)
        num_items = len(items_data)
        totals_start_row = 2 + num_items  # After 2 header rows and items
        
        # Column widths should total 180mm to match other sections
        # Adjust widths based on whether discount column is shown
        if show_discount_col:
            # Sr No, Item Desc, HSN/SAC, Unit Price, Qty, Discount%, Amount, IGST%, IGST Amt, Total
            # Total: 8+42+15+16+10+12+19+13+19+26 = 180mm
            colWidths = [8*mm, 42*mm, 15*mm, 16*mm, 10*mm, 12*mm, 19*mm, 13*mm, 19*mm, 26*mm]
        else:
            # Sr No, Item Desc, HSN/SAC, Unit Price, Qty, Amount, IGST%, IGST Amt, Total
            # Total: 8+45+16+18+12+20+12+20+29 = 180mm
            colWidths = [8*mm, 45*mm, 16*mm, 18*mm, 12*mm, 20*mm, 12*mm, 20*mm, 29*mm]
        
        table = Table(table_data, colWidths=colWidths)
        
        # Build style list dynamically
        style_commands = [
            # Header rows (2 rows)
            ('BACKGROUND', (0, 0), (-1, 1), colors.white),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 1), 7),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('GRID', (0, 0), (-1, 1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, 1), 'MIDDLE'),
        ]
        
        # Add column-specific spans based on whether discount column is shown
        if show_discount_col:
            # Merge columns vertically (rows 0-1) for all columns except IGST (7-8)
            style_commands.extend([
                ('SPAN', (0, 0), (0, 1)),  # Sr No
                ('SPAN', (1, 0), (1, 1)),  # Item Description
                ('SPAN', (2, 0), (2, 1)),  # HSN/SAC
                ('SPAN', (3, 0), (3, 1)),  # Unit Price
                ('SPAN', (4, 0), (4, 1)),  # Qty
                ('SPAN', (5, 0), (5, 1)),  # Discount%
                ('SPAN', (6, 0), (6, 1)),  # Amount
                ('SPAN', (9, 0), (9, 1)),  # Total
                # Merge IGST parent header across columns 7 and 8 in row 0
                ('SPAN', (7, 0), (8, 0)),
            ])
        else:
            # Merge columns vertically (rows 0-1) for all columns except IGST (6-7)
            style_commands.extend([
                ('SPAN', (0, 0), (0, 1)),  # Sr No
                ('SPAN', (1, 0), (1, 1)),  # Item Description
                ('SPAN', (2, 0), (2, 1)),  # HSN/SAC
                ('SPAN', (3, 0), (3, 1)),  # Unit Price
                ('SPAN', (4, 0), (4, 1)),  # Qty
                ('SPAN', (5, 0), (5, 1)),  # Amount
                ('SPAN', (8, 0), (8, 1)),  # Total
                # Merge IGST parent header across columns 6 and 7 in row 0
                ('SPAN', (6, 0), (7, 0)),
            ])
        
        # Data rows (items only) - start from row 2
        style_commands.extend([
            ('FONTSIZE', (0, 2), (-1, num_items + 1), 7),
            ('ALIGN', (0, 2), (0, num_items + 1), 'CENTER'),  # Sr No
            ('ALIGN', (1, 2), (1, num_items + 1), 'LEFT'),    # Description
            ('ALIGN', (2, 2), (2, num_items + 1), 'CENTER'),  # HSN/SAC
            ('ALIGN', (3, 2), (-1, num_items + 1), 'RIGHT'),  # All remaining columns right-aligned
            ('GRID', (0, 2), (-1, num_items + 1), 0.5, colors.black),
            ('VALIGN', (0, 2), (-1, num_items + 1), 'TOP'),
            
            # Totals rows
            ('FONTSIZE', (0, totals_start_row), (-1, -1), 7),
            ('ALIGN', (0, totals_start_row), (-1, -1), 'RIGHT'),
            ('GRID', (0, totals_start_row), (-1, -1), 0.5, colors.black),
            
            # Make totals labels bold and darker for better contrast
            ('FONTNAME', (0, totals_start_row), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, totals_start_row), (0, -1), colors.black),
            
            # Make Total row (last row) bold for both label and amount
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ])
        
        # Add span commands for each totals row (merge all columns except last one)
        for i in range(totals_start_row, len(table_data)):
            style_commands.append(('SPAN', (0, i), (num_cols - 2, i)))
            # Labels in merged cell are right-aligned
            style_commands.append(('ALIGN', (0, i), (0, i), 'RIGHT'))
        
        table.setStyle(TableStyle(style_commands))
        
        elements.append(table)
        return elements
    
    def _build_total_in_words(self):
        """Build total in words section."""
        elements = []
        
        # Calculate grand total with discount
        subtotal = sum(
            item.quantity * float(item.unit_price or 0)
            for item in self.order.items
            if item.inventory_id
        )
        
        # Apply discount
        discount_percentage = float(getattr(self.order, 'discount_percentage', 0) or 0)
        discount_amount = subtotal * (discount_percentage / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        total_igst = sum(
            item.quantity * float(item.unit_price or 0) * (float(item.gst_percentage or 0) / 100)
            for item in self.order.items
            if item.inventory_id
        )
        
        rounding = 0.00  # Can be calculated if needed
        grand_total = subtotal_after_discount + total_igst + rounding
        
        words = number_to_words(grand_total)
        
        data = [[
            Paragraph(f'<b>Total In Words</b><br/><i>Indian Rupee {words} Only</i>', self.styles['NormalText'])
        ]]
        
        table = Table(data, colWidths=[180*mm])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
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
        
        signature_text = '<br/><br/><br/>Authorized Signature'
        
        data = [[
            Paragraph(bank_text, self.styles['SmallText']),
            Paragraph(signature_text, self.styles['NormalText'])
        ]]
        
        table = Table(data, colWidths=[90*mm, 90*mm])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_terms(self):
        """Build terms and conditions section."""
        elements = []
        
        terms_text = (
            '<b>Terms & Conditions</b><br/><br/>'
            '1)Delivery within 12-16 weeks after receiving the confirmed Purchase Order and payment.<br/>'
            '2)Prices are mentioned in the Quote.<br/>'
            '3)Payment shall be made 100% in advance along with Purchase Order.<br/>'
            '4)3 years warranty.<br/>'
            '5)Freight Included.'
        )
        
        data = [[Paragraph(terms_text, self.styles['SmallText'])]]
        
        table = Table(data, colWidths=[180*mm])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(table)
        return elements
    


def generate_estimate_pdf(order: Order) -> BytesIO:
    """
    Generate an ESTIMATE PDF for the given order.
    
    Args:
        order: Order model instance with loaded relationships (customer, items, inventory)
        
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = EstimatePDFGenerator(order)
    return generator.generate()
