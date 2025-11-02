"""
Delivery Challan PDF Generator Service.
Generates Delivery Challan PDFs for dispatched orders.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
from datetime import datetime
import os


class DeliveryChallanPDFGenerator:
    """Generate Delivery Challan PDF for dispatch."""
    
    def __init__(self, dispatch, order, customer):
        from app.core.config import settings
        
        self.dispatch = dispatch
        self.order = order
        self.customer = customer
        self.buffer = BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.elements = []
        
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
            name='DCTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=TA_RIGHT,
            textColor=colors.black
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyDetails',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            spaceBefore=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='BoldText',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))
    
    def _build_header(self):
        """Build header with logo and company details + DELIVERY NOTE title."""
        # Try to load logo
        logo_path = '/Users/praneeth/Documents/PV_enterprise_2/backend/uploads/logo.png'
        logo_element = None
        
        if os.path.exists(logo_path):
            try:
                logo_element = Image(logo_path, width=50*mm, height=20*mm)
            except:
                logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        else:
            logo_element = Paragraph('<b>SREEDEVI<br/>MEDTRADE</b>', self.styles['CompanyName'])
        
        # Create header table: [Logo | DELIVERY NOTE | Company Details]
        header_data = [[
            logo_element,
            Paragraph('<b>DELIVERY NOTE</b>', self.styles['DCTitle']),
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
        
        header_table = Table(header_data, colWidths=[55*mm, 55*mm, 70*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        self.elements.append(header_table)
        self.elements.append(Spacer(1, 5*mm))
    
    def _build_dc_and_customer_info(self):
        """Build DC details and customer information."""
        # DC details
        dc_date = self.dispatch.dispatch_date.strftime('%d.%m.%Y') if self.dispatch.dispatch_date else datetime.now().strftime('%d.%m.%Y')
        
        # Get state from customer
        state_info = self.customer.state or 'Maharashtra'
        
        dc_info_data = [
            ['#', f': {self.dispatch.dispatch_number}', 'Place Of Supply', f': {state_info} (27)'],
            ['Date', f': {dc_date}', '', ''],
        ]
        
        dc_info_table = Table(dc_info_data, colWidths=[20*mm, 70*mm, 40*mm, 50*mm])
        dc_info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        self.elements.append(dc_info_table)
        
        # Customer details - Bill To section
        customer_address = f"{self.customer.name}\n"
        if self.customer.address:
            customer_address += f"{self.customer.address}\n"
        if self.customer.city:
            customer_address += f"{self.customer.city} "
        if self.customer.state:
            customer_address += f"{self.customer.state}\n"
        if self.customer.pincode:
            customer_address += f"{self.customer.pincode} "
        customer_address += f"{self.COMPANY_COUNTRY}"
        
        customer_info_data = [
            ['Bill To'],
            [customer_address],
        ]
        
        
        customer_table = Table(customer_info_data, colWidths=[180*mm])
        customer_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        self.elements.append(customer_table)
    
    def _build_items_table(self):
        """Build the items table with Sr No, Item & Description, HSN/SAC, and Qty."""
        # Header
        header = [['#', 'Item & Description', 'HSN/SAC', 'Qty']]
        
        # Items
        items_data = []
        total_quantity = 0
        
        for idx, dispatch_item in enumerate(self.dispatch.items, 1):
            inventory = dispatch_item.inventory_item
            qty = dispatch_item.quantity
            total_quantity += qty
            
            # Get HSN code
            hsn_code = inventory.hsn_code if hasattr(inventory, 'hsn_code') and inventory.hsn_code else ''
            
            items_data.append([
                str(idx),
                Paragraph(f'<b>{inventory.sku}</b><br/>{inventory.description}', self.styles['SmallText']),
                hsn_code,
                f'{qty:.2f}\npcs'
            ])
        
        # Add total row (merge columns 1-3 for Total Items label)
        total_row = ['Total Items', f'{total_quantity:.2f}\npcs']
        
        # Combine header, items, and total
        table_data = header + items_data + [total_row]
        
        # Column widths: #, Item & Description, HSN/SAC, Qty
        col_widths = [15*mm, 115*mm, 30*mm, 20*mm]
        
        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Styling
        table_style = [
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (2, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # Item rows
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (0, 1), (0, -2), 'CENTER'),  # # center
            ('ALIGN', (2, 1), (-1, -2), 'CENTER'),  # HSN and Qty center
            ('VALIGN', (0, 1), (-1, -2), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            
            # Total row - merge first 3 columns
            ('SPAN', (0, -1), (2, -1)),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('ALIGN', (0, -1), (0, -1), 'RIGHT'),
            ('ALIGN', (1, -1), (1, -1), 'CENTER'),
            ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'),
        ]
        
        items_table.setStyle(TableStyle(table_style))
        self.elements.append(items_table)
        self.elements.append(Spacer(1, 5*mm))
    
    def _build_signature_section(self):
        """Build the authorized signature section."""
        self.elements.append(Spacer(1, 20*mm))
        
        signature_text = Paragraph('Authorized Signature', self.styles['NormalText'])
        signature_table = Table([[signature_text]], colWidths=[180*mm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
        ]))
        
        self.elements.append(signature_table)
    
    def generate(self):
        """Generate the complete delivery challan PDF."""
        self._build_header()
        self._build_dc_and_customer_info()
        self._build_items_table()
        self._build_signature_section()
        
        # Build PDF
        self.doc.build(self.elements)
        
        # Get PDF data
        self.buffer.seek(0)
        return self.buffer


def generate_delivery_challan_pdf(dispatch, order, customer):
    """
    Generate delivery challan PDF for a dispatch.
    
    Args:
        dispatch: Dispatch model instance
        order: Order model instance
        customer: Customer model instance
    
    Returns:
        BytesIO: PDF buffer
    """
    generator = DeliveryChallanPDFGenerator(dispatch, order, customer)
    return generator.generate()
