"""
PDF generation service for Demo Challans.
Uses ReportLab to create professional demo challan PDFs.
"""
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER

from app.models.demo_request import DemoRequest


class DemoChallanPDFGenerator:
    """Generate professional demo challan PDFs."""
    
    def __init__(self, demo_request: DemoRequest):
        from app.core.config import settings
        
        self.demo_request = demo_request
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
        
        # Construct full address
        self.COMPANY_ADDRESS = f"{self.COMPANY_PLOT}, {self.COMPANY_AREA}, {self.COMPANY_CITY}, {self.COMPANY_COUNTRY}"
        
        self.COMPANY_PHONE = "+91 9876543210"
        self.COMPANY_EMAIL = "info@sreedevilifesciences.com"
        self.COMPANY_GST = self.COMPANY_GSTIN
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Company name style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#334155'),
            spaceAfter=10,
            spaceBefore=15,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
    
    def generate(self) -> BytesIO:
        """Generate the PDF and return as BytesIO buffer."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        
        # Header
        story.extend(self._build_header())
        story.append(Spacer(1, 0.3*inch))
        
        # Demo Challan Title
        story.append(Paragraph("DEMO CHALLAN", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        # Demo Info
        story.extend(self._build_demo_info())
        story.append(Spacer(1, 0.3*inch))
        
        # Items Table
        story.extend(self._build_items_table())
        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        story.extend(self._build_footer())
        
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
        
        return elements
    
    def _build_demo_info(self):
        """Build demo request information section."""
        elements = []
        
        # Demo details in a table
        data = [
            ['Demo No:', self.demo_request.number, 'Date:', 
             self.demo_request.created_at.strftime('%d-%b-%Y')],
        ]
        
        table = Table(data, colWidths=[1.2*inch, 3*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#374151')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_items_table(self):
        """Build items table."""
        elements = []
        
        # Table header
        data = [['#', 'Catalog No', 'Item Description', 'Quantity']]
        
        # Cell style for text wrapping
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12
        )
        
        total_quantity = 0
        
        # Add items
        for idx, item in enumerate(self.demo_request.items, 1):
            desc_para = Paragraph(str(item.inventory_item.description or '-'), cell_style)
            
            data.append([
                str(idx),
                item.inventory_item.sku,
                desc_para,
                str(item.quantity)
            ])
            total_quantity += item.quantity
        
        # Add total row
        data.append(['', '', 'Total Items:', str(total_quantity)])
        
        # Create table
        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 3.5*inch, 1*inch])
        
        # Table styling
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # # column
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Catalog No
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Description
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Quantity
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#475569')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('LINEBEFORE', (0, 0), (0, -1), 1, colors.HexColor('#e2e8f0')),
            ('LINEAFTER', (-1, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
            
            # Padding
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Total row styling
            ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, -1), (-1, -1), 11),
            ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
            ('ALIGN', (3, -1), (3, -1), 'CENTER'),
            ('LINEABOVE', (2, -1), (-1, -1), 1.5, colors.HexColor('#475569')),
            ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#f1f5f9')),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_footer(self):
        """Build footer section."""
        elements = []
        
        footer = """
        <para alignment="center">
        <i>This is a computer-generated demo challan.</i><br/>
        Items are provided for demonstration purposes only.
        </para>
        """
        elements.append(Paragraph(footer, self.styles['Normal']))
        
        return elements


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
