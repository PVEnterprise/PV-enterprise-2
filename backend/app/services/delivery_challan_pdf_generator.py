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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
import os


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


class DeliveryChallanPDFGenerator:
    """Generate Delivery Challan PDF for dispatch."""
    
    # Brand Colors
    BRAND_COLOR = colors.HexColor("#1B4F72")
    ACCENT_COLOR = colors.HexColor("#DCECF8")
    
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
            fontSize=18,
            textColor=self.BRAND_COLOR,
            fontName=_FONT,
            leading=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='DCTitle',
            fontSize=18,
            textColor=self.BRAND_COLOR,
            fontName=_FONT,
            alignment=TA_CENTER,
            leading=20
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
            name='SectionHeader',
            fontSize=9,
            fontName=_FONT,
            textColor=colors.white,
            backColor=self.BRAND_COLOR,
            leftIndent=4,
            leading=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontSize=8,
            fontName=_FONT,
            leading=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='BoldText',
            fontSize=10,
            fontName=_FONT,
            leading=12
        ))
    
    def _build_header(self):
        """Build header with logo and company details + DELIVERY NOTE title."""
        # Get dynamic logo path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        logo_path = os.path.join(backend_dir, "uploads", "logo.png")
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
        
        header_table = Table(header_data, colWidths=[65*mm, 50*mm, 65*mm], rowHeights=[26*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
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
        
        dc_info_table = Table(dc_info_data, colWidths=[30*mm, 60*mm, 40*mm, 50*mm])
        dc_info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (-1, -1), _FONT),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        self.elements.append(dc_info_table)
        
        # Customer details - Bill To section (formatted like invoice/estimate)
        customer_text = f'<b>{self.customer.hospital_name or self.customer.name}</b><br/>'
        if self.customer.address:
            customer_text += f'{self.customer.address}<br/>'
        if self.customer.city:
            customer_text += f'{self.customer.city}'
        if self.customer.pincode:
            customer_text += f' - {self.customer.pincode}'
        if self.customer.state:
            customer_text += f'<br/>{self.customer.state}, India'
        
        customer_info_data = [
            [Paragraph('Bill To', self.styles['SectionHeader'])],
            [Paragraph(customer_text, self.styles['NormalText'])],
        ]
        
        customer_table = Table(customer_info_data, colWidths=[180*mm])
        customer_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
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
        
        # Add total row (merge columns 0-2 for Total Items label, quantity in column 3)
        total_row = ['Total Items', '', '', f'{total_quantity:.2f}\npcs']
        
        # Combine header, items, and total
        table_data = header + items_data + [total_row]
        
        # Column widths: #, Item & Description, HSN/SAC, Qty
        col_widths = [15*mm, 115*mm, 30*mm, 20*mm]
        
        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Styling - modern layout with accent color header
        table_style = [
            # Header row - accent color background
            ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT_COLOR),
            ('FONTNAME', (0, 0), (-1, 0), _FONT),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (2, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            
            # Item rows
            ('FONTNAME', (0, 1), (-1, -1), _FONT),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (0, 1), (0, -2), 'CENTER'),  # # center
            ('ALIGN', (2, 1), (-1, -2), 'CENTER'),  # HSN and Qty center
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            
            # Total row - merge first 3 columns
            ('SPAN', (0, -1), (2, -1)),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('ALIGN', (0, -1), (0, -1), 'RIGHT'),
            ('ALIGN', (3, -1), (3, -1), 'CENTER'),
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
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
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
