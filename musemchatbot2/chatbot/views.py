from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.files.base import ContentFile
import json
import uuid
import re
import qrcode
from io import BytesIO
from datetime import datetime
from .models import ChatSession, ChatMessage, Ticket, Booking, ChatBooking
from .utils import send_booking_confirmation_email
import resend

def home(request):
    featured_exhibitions = [
        {
            'title': 'Ancient Civilizations',
            'description': 'Explore artifacts from ancient Egypt, Greece, and Rome',
            'image': '/media/ancientcivilization.jpg',
        },
        {
            'title': 'Modern Art Gallery',
            'description': 'Contemporary masterpieces from around the world',
            'image': '/media/moderart.jpg',
        },
        {
            'title': 'Natural History',
            'description': 'Discover the wonders of our natural world',
            'image': '/media/naturalhistory.jpg',
        }
    ]
    return render(request, 'chatbot/home.html', {'featured_exhibitions': featured_exhibitions})

def about(request):
    museum_info = {
        'history': 'Founded in 1930s by Indian political leader Motilal Nehru, to serve as the residence of the Nehru family',
        'mission': 'To inspire, educate, and remerber the memorial of the Nehru family and their contribution to India. ',
        'highlights': [
            'Over 100,000 artifacts in our collection',
            'State-of-the-art conservation facilities',
            # 'Educational programs for all ages',
            'Regular special exhibitions',
            'Research partnerships with universities'
        ]
    }
    return render(request, 'chatbot/about.html', {'museum_info': museum_info})

def services(request):
    services_info = {
        'guided_tours': {
            'title': 'Guided Tours',
            'description': 'Expert-led tours in multiple languages',
            'duration': '1-2 hours',
            'price': '25 per person'
        },
        'educational_programs': {
            'title': 'Educational Programs',
            'description': 'Interactive learning experiences for schools and groups',
            'age_groups': 'All ages',
            'price': 'Starting at 50 per student'
        },
        'special_events': {
            'title': 'Special Events',
            'description': 'Private events, corporate functions, and celebrations',
            'capacity': 'Up to 500 guests',
            'price': 'Custom quotes available'
        },
        'membership': {
            'title': 'Museum Membership',
            'description': 'Exclusive access and benefits for members',
            'benefits': [
                'Unlimited free admission',
                'Special exhibition previews',
                'Member-only events',
                'Gift shop discounts'
            ]
        }
    }
    return render(request, 'chatbot/services.html', {'services_info': services_info})

def generate_qr_code(booking_data):
    """Generate QR code for booking"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Create human-readable format
    qr_text = f"""
Anand Bhavan Museum - E-Ticket
===============================
Booking Reference: {booking_data['booking_reference']}
Visitor Name: {booking_data['name']}
Ticket Type: {booking_data['ticket_type']}
Quantity: {booking_data['quantity']}
Visit Date: {booking_data['visit_date']}
"""
    # Add data to QR code
    qr.add_data(qr_text)
    qr.make(fit=True)

    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    return buffer.getvalue()

def process_message(message, chat_session, request=None):
    message = message.lower()
    current_state = chat_session.current_booking_state
    booking_data = chat_session.booking_data

    # Create default tickets if they don't exist
    try:
        Ticket.objects.get(ticket_type='ADULT')
    except Ticket.DoesNotExist:
        # Create default tickets
        default_tickets = [
            {'type': 'ADULT', 'price': 100.00, 'description': 'Adult ticket (age 18-64)'},
            {'type': 'CHILD', 'price': 20.00, 'description': 'Child ticket (age 5-17)'},
            {'type': 'SENIOR', 'price': 20.00, 'description': 'Senior ticket (age 65+)'},
            {'type': 'STUDENT', 'price': 50.00, 'description': 'Student ticket (with valid ID)'}
        ]
        for ticket in default_tickets:
            Ticket.objects.create(
                ticket_type=ticket['type'],
                price=ticket['price'],
                description=ticket['description']
            )

    # Start booking process
    if 'book' in message or 'ticket' in message:
        if current_state == 'NONE':
            chat_session.current_booking_state = 'ASKING_NAME'
            chat_session.save()
            return "I'll help you book your tickets! First, could you please tell me your name?"

    # Handle booking states
    if current_state == 'ASKING_NAME':
        booking_data['name'] = message.title()  # Capitalize first letter of each word
        chat_session.current_booking_state = 'ASKING_EMAIL'
        chat_session.booking_data = booking_data
        chat_session.save()
        return "Thank you! Now, please provide your email address."

    elif current_state == 'ASKING_EMAIL':
        if not re.match(r"[^@]+@[^@]+\.[^@]+", message):
            return "That doesn't look like a valid email address. Please try again."
        
        booking_data['email'] = message.lower()
        chat_session.current_booking_state = 'ASKING_PHONE'
        chat_session.booking_data = booking_data
        chat_session.save()
        return "Great! Please provide your phone number."

    elif current_state == 'ASKING_PHONE':
        # Remove any non-digit characters from phone number
        phone = re.sub(r'\D', '', message)
        if len(phone) < 10:
            return "Please provide a valid phone number with at least 10 digits."
        
        booking_data['phone'] = phone
        chat_session.current_booking_state = 'ASKING_TICKET_TYPE'
        chat_session.booking_data = booking_data
        chat_session.save()
        
        ticket_types = Ticket.objects.all()
        response = "What type of ticket would you like?\n\n"
        for ticket in ticket_types:
            response += f"• {ticket.ticket_type}: ${ticket.price} - {ticket.description}\n"
        return response

    elif current_state == 'ASKING_TICKET_TYPE':
        ticket_type = message.upper()
        try:
            # Verify ticket type exists
            ticket = Ticket.objects.get(ticket_type=ticket_type)
            booking_data['ticket_type'] = ticket_type
            chat_session.current_booking_state = 'ASKING_QUANTITY'
            chat_session.booking_data = booking_data
            chat_session.save()
            return "How many tickets would you like?"
        except Ticket.DoesNotExist:
            valid_types = [t.ticket_type for t in Ticket.objects.all()]
            return f"Please select a valid ticket type: {', '.join(valid_types)}"

    elif current_state == 'ASKING_QUANTITY':
        try:
            quantity = int(message)
            if quantity <= 0:
                return "Please enter a valid number greater than 0."
            if quantity > 10:
                return "Maximum 10 tickets per booking. Please enter a smaller number."
            
            booking_data['quantity'] = quantity
            chat_session.current_booking_state = 'ASKING_DATE'
            chat_session.booking_data = booking_data
            chat_session.save()
            return "For which date would you like to book? (Please use YYYY-MM-DD format)"
        except ValueError:
            return "Please enter a valid number."

    elif current_state == 'ASKING_DATE':
        try:
            visit_date = datetime.strptime(message, '%Y-%m-%d').date()
            today = timezone.now().date()
            max_date = today + timezone.timedelta(days=365)  # Booking up to 1 year in advance
            
            if visit_date < today:
                return "Please select a future date."
            if visit_date > max_date:
                return f"Bookings are only available up to {max_date.strftime('%Y-%m-%d')}. Please select an earlier date."
            
            booking_data['visit_date'] = message
            
            # Calculate total amount
            ticket = Ticket.objects.get(ticket_type=booking_data['ticket_type'])
            total_amount = ticket.price * booking_data['quantity']
            booking_data['total_amount'] = float(total_amount)
            
            # Create booking reference
            booking_reference = f"BK{uuid.uuid4().hex[:8].upper()}"
            booking_data['booking_reference'] = booking_reference
            
            chat_session.current_booking_state = 'CONFIRMING'
            chat_session.booking_data = booking_data
            chat_session.save()
            
            return f"""Please confirm your booking details:

Booking Reference: {booking_data['booking_reference']}
Name: {booking_data['name']}
Email: {booking_data['email']}
Phone: {booking_data['phone']}
Ticket Type: {booking_data['ticket_type']}
Quantity: {booking_data['quantity']}
Visit Date: {booking_data['visit_date']}
Total Amount: ${booking_data['total_amount']:.2f}

Type 'confirm' to proceed with payment or 'cancel' to start over."""
            
        except ValueError:
            return "Please enter a valid date in YYYY-MM-DD format (e.g., 2024-03-15)."

    elif current_state == 'CONFIRMING':
        if message.lower() == 'confirm':
            try:
                # Create and save the booking in one step
                chat_booking = ChatBooking.objects.create(
                    name=booking_data['name'],
                    email=booking_data['email'],
                    phone=booking_data['phone'],
                    ticket_type=booking_data['ticket_type'],
                    quantity=booking_data['quantity'],
                    visit_date=booking_data['visit_date'],
                    total_amount=booking_data['total_amount'],
                    booking_reference=booking_data['booking_reference'],
                    chat_session=chat_session,
                    payment_status='COMPLETED'
                )
                
                # Send confirmation email with QR code
                email_sent = send_booking_confirmation_email(chat_booking, request)
                
                # Reset booking state
                chat_session.current_booking_state = 'NONE'
                chat_session.booking_data = {}
                chat_session.save()
                
                email_status = "📧 A confirmation email has been sent to your email address." if email_sent else "⚠️ There was an issue sending the confirmation email. Please contact support."
                
                # Get QR code URL - should be available since it's generated in the model's save method
                qr_code_url = chat_booking.qr_code.url if chat_booking.qr_code else None
                
                if not qr_code_url:
                    logger.error(f"QR code not generated for booking {chat_booking.booking_reference}")
                    return "Sorry, there was an error generating your booking QR code. Please contact support."
                
                return f"""🎫 Thank you for your booking! Here's your receipt:

BOOKING CONFIRMATION
===================
Booking Reference: {chat_booking.booking_reference}
Name: {chat_booking.name}
Email: {chat_booking.email}
Phone: {chat_booking.phone}
Ticket Type: {chat_booking.ticket_type}
Quantity: {chat_booking.quantity}
Visit Date: {chat_booking.visit_date}
Total Amount Paid: ${chat_booking.total_amount:.2f}

✅ Your booking is confirmed!
{email_status}
🎟️ Please save your booking reference for future reference.

<div class="qr-code-container" style="text-align: center; margin: 20px 0;">
    <p><strong>Your QR Code Ticket:</strong></p>
    <img src="{qr_code_url}" alt="Booking QR Code" style="max-width: 200px; margin: 10px auto; display: block; border: 2px solid #ddd; padding: 10px; border-radius: 5px;">
    <p style="font-size: 0.9em; color: #666;">Please present this QR code when you arrive at the museum.</p>
</div>

We look forward to your visit! Is there anything else I can help you with?"""
                
            except Exception as e:
                logger.error(f"Error processing booking: {str(e)}")
                return "Sorry, there was an error processing your booking. Please try again or contact support."
            
        elif message.lower() == 'cancel':
            chat_session.current_booking_state = 'NONE'
            chat_session.booking_data = {}
            chat_session.save()
            return "Booking cancelled. How else can I help you?"
            
        return "Please type 'confirm' to complete your booking or 'cancel' to start over."

    # Handle other queries
    if 'price' in message or 'cost' in message:
        tickets = Ticket.objects.all()
        response = "Here are our ticket prices:\n\n"
        for ticket in tickets:
            response += f"• {ticket.ticket_type}: ${ticket.price} - {ticket.description}\n"
        return response
    
    elif 'help' in message:
        return """I can help you with:
• Booking tickets
• Checking ticket prices
• Information about exhibitions
• Tour schedules
• Opening hours

Just let me know what you'd like to know!"""
    
    elif 'hour' in message or 'time' in message:
        return """Our opening hours are:
• Monday - Friday: 9:00 AM - 6:00 PM
• Saturday - Sunday: 10:00 AM - 4:00 PM"""
    
    else:
        return "I'm not sure I understand. Would you like to book tickets, check prices, or get general information?"

@csrf_exempt
def chat_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message')
        session_id = data.get('session_id')
        
        # Create or get chat session
        if not session_id:
            session_id = str(uuid.uuid4())
            chat_session = ChatSession.objects.create(
                session_id=session_id,
                user=request.user if request.user.is_authenticated else None
            )
        else:
            chat_session = ChatSession.objects.get(session_id=session_id)
        
        # Save user message
        ChatMessage.objects.create(
            session=chat_session,
            message_type='USER',
            content=message
        )
        
        # Process message and generate response
        response = process_message(message, chat_session, request)
        
        # Save bot response
        ChatMessage.objects.create(
            session=chat_session,
            message_type='BOT',
            content=response
        )
        
        return JsonResponse({
            'response': response,
            'session_id': session_id
        })
    
    return JsonResponse({'error': 'Invalid request method'})

@login_required
def booking_history(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'chatbot/booking_history.html', {'bookings': bookings})

@login_required
def create_booking(request):
    if request.method == 'POST':
        # Process booking form data
        ticket_type = request.POST.get('ticket_type')
        quantity = int(request.POST.get('quantity'))
        visit_date = request.POST.get('visit_date')
        
        ticket = Ticket.objects.get(ticket_type=ticket_type)
        total_amount = ticket.price * quantity
        
        # Generate unique booking reference
        booking_reference = f"BK{uuid.uuid4().hex[:8].upper()}"
        
        Booking.objects.create(
            user=request.user,
            ticket=ticket,
            quantity=quantity,
            booking_date=timezone.now().date(),
            visit_date=visit_date,
            total_amount=total_amount,
            booking_reference=booking_reference
        )
        
        return redirect('booking_history')
    
    tickets = Ticket.objects.all()
    return render(request, 'chatbot/create_booking.html', {'tickets': tickets})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'chatbot/register.html', {'form': form})

def chat(request):
    return render(request, 'chatbot/chat.html')

@csrf_exempt
def verify_ticket(request):
    """
    Verify ticket QR code and display booking information
    """
    if request.method == 'POST':
        try:
            # Get QR code data
            data = request.POST.get('qr_data')
            if not data:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No QR code data provided'
                })

            # Extract booking reference from the QR code data
            booking_ref_match = re.search(r'Booking Reference: ([A-Z0-9]+)', data)
            if not booking_ref_match:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid QR code format'
                })

            booking_reference = booking_ref_match.group(1)

            # Find the booking
            try:
                booking = ChatBooking.objects.get(booking_reference=booking_reference)
                
                # Check if the booking is valid
                today = timezone.now().date()
                if booking.visit_date < today:
                    status = "EXPIRED"
                    message = "This ticket has expired"
                elif booking.visit_date > today:
                    status = "FUTURE"
                    message = "This ticket is for a future date"
                else:
                    status = "VALID"
                    message = "Valid ticket for today"

                # Return booking information in a structured format
                return render(request, 'chatbot/verify_ticket.html', {
                    'status': status,
                    'message': message,
                    'booking': {
                        'reference': booking.booking_reference,
                        'name': booking.name,
                        'ticket_type': booking.ticket_type,
                        'quantity': booking.quantity,
                        'visit_date': booking.visit_date,
                        'total_amount': booking.total_amount,
                    }
                })

            except ChatBooking.DoesNotExist:
                return render(request, 'chatbot/verify_ticket.html', {
                    'status': 'INVALID',
                    'message': 'Booking not found',
                    'booking': None
                })

        except Exception as e:
            logger.error(f"Error verifying ticket: {str(e)}")
            return render(request, 'chatbot/verify_ticket.html', {
                'status': 'ERROR',
                'message': 'Error processing QR code',
                'booking': None
            })

    return render(request, 'chatbot/verify_ticket.html', {
        'status': 'ERROR',
        'message': 'Invalid request method',
        'booking': None
    })
