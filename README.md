# Museum Ticket Booking Chatbot

This project is a Django-based museum ticket booking system with an integrated chatbot interface.

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd musemchatbot2
   ```

2. **Set up Python Virtual Environment**
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install django
   pip install django-crispy-forms
   ```

4. **Database Setup**
   ```bash
   # Navigate to the project directory containing manage.py
   cd musemchatbot2

   # Create database migrations
   python manage.py makemigrations

   # Apply migrations
   python manage.py migrate
   ```

5. **Create Admin User**
   ```bash
   python manage.py createsuperuser
   # Follow the prompts to create username and password
   ```

## Running the Project

1. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

2. **Access the Application**
   - Main website: http://127.0.0.1:8000/
   - Admin interface: http://127.0.0.1:8000/admin

## Using the Admin Interface

1. **Login to Admin Panel**
   - Go to http://127.0.0.1:8000/admin
   - Enter your superuser credentials

2. **View and Manage Data**
   You can view and manage the following:

   - **Tickets**
     - View all ticket types
     - Add/modify ticket prices
     - Edit ticket descriptions

   - **Chat Bookings**
     - View all chatbot bookings
     - See booking details like:
       - Reference numbers
       - Customer information
       - Ticket quantities
       - Visit dates
       - Payment status

   - **Chat Sessions**
     - Monitor active chat sessions
     - View conversation states
     - Track booking progress

   - **Chat Messages**
     - View conversation history
     - Filter messages by type
     - Search message content

3. **Admin Features**
   - Filter records by various fields
   - Search functionality
   - Sort by columns
   - Export data (if needed)

## Project Structure

```
musemchatbot2/
├── chatbot/                 # Main application
│   ├── models.py           # Database models
│   ├── views.py            # View logic
│   ├── admin.py           # Admin interface configuration
│   └── templates/         # HTML templates
├── manage.py              # Django management script
└── requirements.txt       # Project dependencies
```

## Troubleshooting

1. **Database Issues**
   - If you encounter database errors, try:
     ```bash
     python manage.py makemigrations
     python manage.py migrate
     ```

2. **Admin Access Issues**
   - If you can't access admin, create a new superuser:
     ```bash
     python manage.py createsuperuser
     ```

3. **Server Not Starting**
   - Ensure you're in the correct directory (musemchatbot2)
   - Check if port 8000 is available
   - Verify virtual environment is activated

## Support

For any issues or questions, please:
1. Check the error messages in the console
2. Verify you're in the correct directory
3. Ensure all dependencies are installed
4. Make sure the database is properly migrated 