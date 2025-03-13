from django.contrib import admin
from .models import Ticket, ChatBooking, Booking, ChatSession, ChatMessage

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_type', 'price', 'description')
    list_filter = ('ticket_type',)
    search_fields = ('ticket_type', 'description')

@admin.register(ChatBooking)
class ChatBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'name', 'email', 'ticket_type', 'quantity', 
                   'visit_date', 'total_amount', 'payment_status', 'created_at')
    list_filter = ('ticket_type', 'payment_status', 'created_at', 'visit_date')
    search_fields = ('booking_reference', 'name', 'email', 'phone')
    readonly_fields = ('booking_reference', 'created_at')
    ordering = ('-created_at',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'ticket', 'quantity', 
                   'visit_date', 'total_amount', 'created_at')
    list_filter = ('ticket', 'booking_date', 'visit_date', 'created_at')
    search_fields = ('booking_reference', 'user__username', 'user__email')
    readonly_fields = ('booking_reference', 'created_at')
    ordering = ('-created_at',)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'current_booking_state', 
                   'created_at', 'last_interaction')
    list_filter = ('current_booking_state', 'created_at', 'last_interaction')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('created_at', 'last_interaction')
    ordering = ('-last_interaction',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('get_session_id', 'message_type', 'content_preview', 'timestamp')
    list_filter = ('message_type', 'timestamp')
    search_fields = ('content', 'session__session_id')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)

    def get_session_id(self, obj):
        return obj.session.session_id
    get_session_id.short_description = 'Session ID'

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
