import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

class DemoEmailService:
    def __init__(self):
        self.smtp_server = settings.EMAIL_HOST
        self.smtp_port = settings.EMAIL_PORT
        self.smtp_username = settings.EMAIL_HOST_USER
        self.smtp_password = settings.EMAIL_HOST_PASSWORD
        self.from_email = settings.DEFAULT_FROM_EMAIL
    
    def send_demo_confirmation(self, demo_booking):
        """Send demo confirmation email with Google Meet link"""
        try:
            subject = f"Demo Scheduled: Restaurant Voice Assistant - {demo_booking.demo_date.strftime('%B %d, %Y at %I:%M %p')}"
            
            # Create HTML email content
            html_content = render_to_string('emails/demo_confirmation.html', {
                'demo': demo_booking,
                'company_name': 'SmoothieQ',
                'support_email': settings.DEFAULT_FROM_EMAIL
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.from_email
            message['To'] = demo_booking.email
            
            # Add both plain text and HTML versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Demo confirmation email sent to {demo_booking.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send demo confirmation email: {e}")
            return False
    
    def send_demo_reminder(self, demo_booking):
        """Send demo reminder email"""
        try:
            subject = f"Reminder: Demo Tomorrow - Restaurant Voice Assistant"
            
            html_content = render_to_string('emails/demo_reminder.html', {
                'demo': demo_booking,
                'company_name': 'SmoothieQ'
            })
            
            text_content = strip_tags(html_content)
            
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.from_email
            message['To'] = demo_booking.email
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            message.attach(text_part)
            message.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send demo reminder email: {e}")
            return False
