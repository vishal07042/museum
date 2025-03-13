from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
import os
import logging
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Image
import tempfile
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

def get_absolute_url(request, relative_url):
    """
    Convert a relative URL to an absolute URL
    """
    if request:
        protocol = 'https' if request.is_secure() else 'http'
        domain = get_current_site(request).domain
    else:
        protocol = 'http'
        domain = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    
    # Ensure the URL starts with a single forward slash
    if relative_url.startswith('/'):
        relative_url = relative_url[1:]
    
    return f"{protocol}://{domain}/{relative_url}"

def generate_pdf_ticket(booking, qr_code_path):
    """
    Generate a PDF ticket with booking details and QR code
    """
    try:
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
            
            # Create PDF
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            
            try:
                # Add museum logo/name - using standard font
                c.setFont("Times-Bold", 24)
                c.drawCentredString(width/2, height-1*inch, settings.MUSEUM_NAME)
                
                # Add "E-Ticket" text
                c.setFont("Times-Bold", 18)
                c.drawCentredString(width/2, height-1.5*inch, "E-Ticket")
                
                # Add booking details
                c.setFont("Times-Roman", 12)
                details_start_y = height - 2.5*inch
                c.drawString(1*inch, details_start_y, f"Booking Reference: {booking.booking_reference}")
                c.drawString(1*inch, details_start_y - 0.3*inch, f"Visitor Name: {booking.name}")
                c.drawString(1*inch, details_start_y - 0.6*inch, f"Visit Date: {booking.visit_date}")
                c.drawString(1*inch, details_start_y - 0.9*inch, f"Ticket Type: {booking.ticket_type}")
                c.drawString(1*inch, details_start_y - 1.2*inch, f"Quantity: {booking.quantity}")
                c.drawString(1*inch, details_start_y - 1.5*inch, f"Total Amount: ${booking.total_amount:.2f}")
                
                # Add QR code if available
                if os.path.exists(qr_code_path):
                    qr_img = ImageReader(qr_code_path)
                    c.drawImage(qr_img, width/2 - 1.5*inch, height-6*inch, width=3*inch, height=3*inch)
                
                c.save()
                return pdf_path
                
            except Exception as e:
                logger.error(f"Error generating PDF content: {str(e)}")
                if os.path.exists(pdf_path):
                    try:
                        os.unlink(pdf_path)
                    except:
                        pass
                return None
                
    except Exception as e:
        logger.error(f"Error in generate_pdf_ticket: {str(e)}")
        return None

def send_booking_confirmation_email(booking, request=None):
    """
    Send a booking confirmation email using Django's email functionality
    """
    logger.info(f"Starting email sending process for booking {booking.booking_reference}")
    try:
        # Get absolute URL for QR code
        qr_code_url = None
        if booking.qr_code:
            try:
                if request:
                    # Get the full URL including domain
                    qr_code_url = request.build_absolute_uri(booking.qr_code.url)
                else:
                    # If no request object, construct URL using settings
                    domain = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
                    protocol = 'https' if not settings.DEBUG else 'http'
                    qr_code_url = f"{protocol}://{domain}{booking.qr_code.url}"
                
                logger.info(f"Generated QR code URL: {qr_code_url}")
            except Exception as e:
                logger.error(f"Error generating QR code URL: {str(e)}")
                qr_code_url = None

        # Prepare email content
        context = {
            'booking': booking,
            'museum_name': settings.MUSEUM_NAME,
            'museum_address': settings.MUSEUM_ADDRESS,
            'museum_contact': settings.MUSEUM_CONTACT,
            'booking_reference': booking.booking_reference,
            'visit_date': booking.visit_date,
            'ticket_type': booking.ticket_type,
            'quantity': booking.quantity,
            'total_amount': booking.total_amount,
            'qr_code_url': qr_code_url,
            'has_pdf': False
        }
        
        # Render email template
        try:
            email_body = render_to_string('chatbot/email/booking_confirmation.html', context)
            logger.info("Successfully rendered email template")
        except Exception as e:
            logger.error(f"Error rendering email template: {str(e)}")
            return False

        # Create email message
        try:
            email = EmailMessage(
                subject=f'{settings.MUSEUM_NAME} - Booking Confirmation - {booking.booking_reference}',
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[booking.email],
            )
            email.content_subtype = "html"
            
            # Attach QR code as an image
            if booking.qr_code:
                try:
                    # Get the QR code file path
                    qr_code_path = booking.qr_code.path
                    if os.path.exists(qr_code_path):
                        with open(qr_code_path, 'rb') as qr_file:
                            email.attach(
                                f'qr_code_{booking.booking_reference}.png',
                                qr_file.read(),
                                'image/png'
                            )
                        logger.info("Successfully attached QR code to email")
                except Exception as e:
                    logger.error(f"Error attaching QR code to email: {str(e)}")
            
            # Send email
            email.send(fail_silently=False)
            logger.info(f"Successfully sent booking confirmation email to {booking.email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error in send_booking_confirmation_email: {str(e)}")
        return False 