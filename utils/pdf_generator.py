from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

def generate_booking_summary_pdf(booking_data, output_path):
    """
    Generates a PDF summary of the booking.
    
    Args:
        booking_data (dict): Dictionary containing booking information
        output_path (str): Path where the PDF should be saved
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph("Booking Summary", title_style))
    elements.append(Spacer(1, 20))
    
    # Booking Details
    data = [
        ["Booking ID:", str(booking_data.get('id', 'N/A'))],
        ["Area Name:", booking_data.get('area_name', 'N/A')],
        ["Start Date:", booking_data.get('start_date', 'N/A')],
        ["End Date:", booking_data.get('end_date', 'N/A')],
        ["Number of People:", str(booking_data.get('people', 'N/A'))],
        ["Total Cost:", f"${booking_data.get('total_cost', 0):.2f}"],
        ["Status:", booking_data.get('status', 'N/A')],
        ["Booking Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ]
    
    # Create table
    table = Table(data, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Terms and Conditions
    terms_style = ParagraphStyle(
        'Terms',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey
    )
    elements.append(Paragraph("Terms and Conditions:", styles['Heading2']))
    elements.append(Paragraph(
        "1. All bookings are subject to availability\n"
        "2. Cancellations must be made 24 hours in advance\n"
        "3. No refunds for no-shows\n"
        "4. Maximum capacity must be strictly adhered to",
        terms_style
    ))
    
    # Build PDF
    doc.build(elements) 