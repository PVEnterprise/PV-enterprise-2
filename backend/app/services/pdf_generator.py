"""
PDF generation service for quotations.
Uses ReportLab to create professional quotation PDFs.
"""
import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from app.models.quotation import Quotation
from app.models.order import Order
from app.models.customer import Customer


class QuotationPDFGenerator:
    """Generate professional quotation PDFs."""
    
    # Company Information
    COMPANY_NAME = "Medical Equipment Supply"
    COMPANY_ADDRESS = "123 Medical District, Healthcare City"
    COMPANY_PHONE = "+91 1234567890"
    COMPANY_EMAIL = "info@medicalequipment.com"
    COMPANY_GST = "29ABCDE1234F1Z5"
    
    def __init__(self, quotation: Quotation):
        self.quotation = quotation
        self.order: Order = quotation.order
        self.customer: Customer = self.order.customer
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Modern company name style - Dark slate
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#0f172a'),  # Dark slate
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Modern section heading - Slate gray
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#334155'),  # Slate gray
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Right aligned text
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT
        ))
    
    def generate(self) -> BytesIO:
        """Generate the PDF and return as BytesIO buffer."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=0.4*inch,  # Reduced margins for more space
            leftMargin=0.4*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        # Build the PDF content
        story = []
        
        # Header
        story.extend(self._build_header())
        story.append(Spacer(1, 0.3*inch))
        
        # Quotation Info
        story.extend(self._build_quotation_info())
        story.append(Spacer(1, 0.2*inch))
        
        # Customer Info
        story.extend(self._build_customer_info())
        story.append(Spacer(1, 0.3*inch))
        
        # Items Table
        story.extend(self._build_items_table())
        story.append(Spacer(1, 0.3*inch))
        
        # Totals
        story.extend(self._build_totals())
        story.append(Spacer(1, 0.3*inch))
        
        # Terms and Conditions
        story.extend(self._build_terms())
        
        # Build PDF
        doc.build(story)
        self.buffer.seek(0)
        return self.buffer
    
    def _build_header(self):
        """Build company header."""
        elements = []
        
        # Company name
        elements.append(Paragraph(self.COMPANY_NAME, self.styles['CompanyName']))
        
        # Company details
        company_info = f"""
        <para alignment="center">
        {self.COMPANY_ADDRESS}<br/>
        Phone: {self.COMPANY_PHONE} | Email: {self.COMPANY_EMAIL}<br/>
        GST No: {self.COMPANY_GST}
        </para>
        """
        elements.append(Paragraph(company_info, self.styles['Normal']))
        
        # Horizontal line
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_quotation_info(self):
        """Build quotation information section."""
        elements = []
        
        # Title
        elements.append(Paragraph("QUOTATION", self.styles['SectionHeading']))
        
        # Quotation details in a table
        data = [
            ['Quotation No:', self.quotation.quote_number, 'Date:', 
             self.quotation.created_at.strftime('%d-%b-%Y')],
            ['Order No:', self.order.order_number, 'Valid Until:', 
             self.quotation.valid_until.strftime('%d-%b-%Y') if self.quotation.valid_until else 'N/A'],
        ]
        
        table = Table(data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#374151')),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_customer_info(self):
        """Build customer information section."""
        elements = []
        
        elements.append(Paragraph("Bill To:", self.styles['SectionHeading']))
        
        customer_info = f"""
        <b>{self.customer.hospital_name}</b><br/>
        {self.customer.address or ''}<br/>
        {self.customer.city or ''}, {self.customer.state or ''} {self.customer.pincode or ''}<br/>
        Phone: {self.customer.phone} | Email: {self.customer.email}
        """
        if self.customer.gst_number:
            customer_info += f"<br/>GST No: {self.customer.gst_number}"
        
        elements.append(Paragraph(customer_info, self.styles['Normal']))
        return elements
    
    def _build_items_table(self):
        """Build items table with all line items."""
        elements = []
        
        # Table header with Rs. prefix
        data = [['#', 'Description', 'Qty', 'Unit Price\n(Rs.)', 'Amount\n(Rs.)', 'GST %', 'Tax Amt\n(Rs.)', 'Total Amt\n(Rs.)']]
        
        # Create a style for table cell text wrapping
        from reportlab.lib.styles import ParagraphStyle
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11
        )
        
        # Add items
        for idx, item in enumerate(self.quotation.items, 1):
            # Get GST percentage - try to get from item or use default
            gst_pct = getattr(item, 'gst_percentage', self.quotation.gst_rate)
            
            # Calculate tax amount (convert Decimal to float for calculation)
            tax_amount = float(item.line_total) * (float(gst_pct) / 100)
            
            # Calculate total amount (line_total + tax)
            total_amount = float(item.line_total) + tax_amount
            
            # Wrap description in Paragraph for text wrapping
            desc_para = Paragraph(str(item.description), cell_style)
            
            data.append([
                str(idx),
                desc_para,  # Use Paragraph for wrapping
                str(item.quantity),
                f"{item.unit_price:,.2f}",      # Amount only, Rs. in header
                f"{item.line_total:,.2f}",      # Amount only
                f"{float(gst_pct):.1f}%",
                f"{tax_amount:,.2f}",           # Amount only
                f"{total_amount:,.2f}"          # Amount only
            ])
        
        # Create table with wider columns (using more available space)
        table = Table(data, colWidths=[0.35*inch, 2.2*inch, 0.5*inch, 1.0*inch, 1.0*inch, 0.6*inch, 1.0*inch, 1.1*inch])
        
        # Modern table styling - Slate color scheme
        table.setStyle(TableStyle([
            # Header row - Dark slate
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),  # Slate gray
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows - Modern clean look
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # # column
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Description column
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Qty column
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Unit Price - right aligned
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Amount - right aligned
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # GST % column
            ('ALIGN', (6, 1), (6, -1), 'RIGHT'),   # Tax Amount - right aligned
            ('ALIGN', (7, 1), (7, -1), 'RIGHT'),   # Total Amount - right aligned
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Modern grid - lighter borders
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#475569')),  # Thick slate line under header
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),  # Light lines between rows
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor('#475569')),  # Thick line at bottom
            ('LINEBEFORE', (0, 0), (0, -1), 1, colors.HexColor('#e2e8f0')),  # Left border
            ('LINEAFTER', (-1, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),  # Right border
            
            # Modern alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            
            # Generous padding for modern look
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_totals(self):
        """Build totals section."""
        elements = []
        
        # Totals data (removed GST line as it's shown per item)
        data = [
            ['Subtotal:', f"Rs. {self.quotation.subtotal:,.2f}"],
        ]
        
        if self.quotation.discount_amount and self.quotation.discount_amount > 0:
            data.append([
                f'Discount ({self.quotation.discount_percentage}%):', 
                f"- Rs. {self.quotation.discount_amount:,.2f}"
            ])
        
        # Add total with tax (GST details are per item, so just show final total)
        data.append(['Total Amount (incl. Tax):', f"Rs. {self.quotation.total_amount:,.2f}"])
        
        # Create table (right-aligned)
        table = Table(data, colWidths=[5*inch, 1.5*inch])
        
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#0f172a')),  # Dark slate
            ('LINEABOVE', (0, -1), (-1, -1), 2.5, colors.HexColor('#475569')),  # Thicker slate line
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),  # Light slate background for total
        ]))
        
        elements.append(table)
        return elements
    
    def _build_terms(self):
        """Build terms and conditions section."""
        elements = []
        
        elements.append(Paragraph("Terms & Conditions:", self.styles['SectionHeading']))
        
        terms = f"""
        <b>Payment Terms:</b> {self.quotation.payment_terms or 'Net 30 days'}<br/>
        <b>Delivery Terms:</b> {self.quotation.delivery_terms or 'Ex-warehouse'}<br/>
        """
        
        # Notes removed as per requirement
        
        elements.append(Paragraph(terms, self.styles['Normal']))
        
        # Footer
        elements.append(Spacer(1, 0.3*inch))
        footer = """
        <para alignment="center">
        <i>This is a computer-generated quotation and does not require a signature.</i><br/>
        Thank you for your business!
        </para>
        """
        elements.append(Paragraph(footer, self.styles['Normal']))
        
        return elements


def generate_quotation_pdf(quotation: Quotation) -> BytesIO:
    """
    Generate a PDF for the given quotation.
    
    Args:
        quotation: Quotation model instance with loaded relationships
        
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = QuotationPDFGenerator(quotation)
    return generator.generate()


def generate_order_quotation_pdf(order: Order) -> BytesIO:
    """
    Generate a quotation PDF directly from an order (without Quotation model).
    Used for quick quotation generation from approved orders.
    
    Args:
        order: Order model instance with loaded relationships
        
    Returns:
        BytesIO buffer containing the PDF
    """
    from datetime import date, timedelta
    
    # Create a temporary quotation-like object for PDF generation
    class TempQuotation:
        def __init__(self, order):
            self.order = order
            self.quote_number = f"QUOTE-{order.order_number}"
            self.created_at = order.created_at
            self.valid_until = date.today() + timedelta(days=30)
            self.payment_terms = "Net 30 days"
            self.delivery_terms = "Ex-warehouse"
            self.notes = order.notes
            self.gst_rate = 18.00  # Default GST rate
            self.discount_percentage = 0.00
            self.discount_amount = 0.00
            
            # Calculate totals from order items
            self.subtotal = sum(
                item.quantity * (item.unit_price or 0)
                for item in order.items
                if item.unit_price
            )
            
            # Calculate GST (weighted average from items)
            total_gst = sum(
                item.quantity * (item.unit_price or 0) * (item.gst_percentage or 18) / 100
                for item in order.items
                if item.unit_price
            )
            self.gst_amount = total_gst
            self.total_amount = self.subtotal + self.gst_amount
            
            # Convert order items to quotation items format
            self.items = []
            for item in order.items:
                if item.inventory_item and item.unit_price:
                    temp_item = type('obj', (object,), {
                        'description': item.inventory_item.item_name,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'line_total': item.quantity * item.unit_price,
                        'gst_percentage': item.gst_percentage or 18.00  # Include GST percentage
                    })()
                    self.items.append(temp_item)
    
    temp_quotation = TempQuotation(order)
    generator = QuotationPDFGenerator(temp_quotation)
    return generator.generate()
