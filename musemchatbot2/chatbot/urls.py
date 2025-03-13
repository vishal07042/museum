from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('chat/', views.chat, name='chat'),
    path('chat/message/', views.chat_message, name='chat_message'),
    path('register/', views.register, name='register'),
    path('booking-history/', views.booking_history, name='booking_history'),
    path('create-booking/', views.create_booking, name='create_booking'),
    path('verify-ticket/', views.verify_ticket, name='verify_ticket'),
] 