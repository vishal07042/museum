from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import os

class Ticket(models.Model):
    TICKET_TYPES = [
        ('ADULT', 'Adult'),
        ('CHILD', 'Child'),
        ('SENIOR', 'Senior'),
        ('STUDENT', 'Student'),
    ]
    
    ticket_type = models.CharField(max_length=10, choices=TICKET_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    
    def __str__(self):
        return f"{self.ticket_type} - ${self.price}"

class ChatBooking(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    ticket_type = models.CharField(max_length=10, choices=Ticket.TICKET_TYPES)
    quantity = models.IntegerField()
    visit_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    booking_reference = models.CharField(max_length=20, unique=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    chat_session = models.ForeignKey('ChatSession', on_delete=models.SET_NULL, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"Booking {self.booking_reference} - {self.name}"

    def generate_qr_code(self):
        """Generate QR code for booking"""
        if self.qr_code:
            return  # Don't generate if QR code already exists
            
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"""
Booking Reference: {self.booking_reference}
Name: {self.name}
Ticket Type: {self.ticket_type}
Quantity: {self.quantity}
Visit Date: {self.visit_date}
        """
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_code_{self.booking_reference}.png'
        
        self.qr_code.save(filename, File(buffer), save=False)
        
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    booking_date = models.DateField()
    visit_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    booking_reference = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Booking {self.booking_reference} - {self.user.username}"

class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_interaction = models.DateTimeField(auto_now=True)
    language = models.CharField(max_length=10, default='en')
    current_booking_state = models.CharField(max_length=20, default='NONE')
    booking_data = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Chat Session {self.session_id}"

class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('USER', 'User Message'),
        ('BOT', 'Bot Message'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=4, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.message_type} - {self.timestamp}"
