import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        # Path to your service account credentials JSON file
        self.credentials_path = os.path.join(settings.BASE_DIR, 'credentials', 'google-service-account.json')
        self.calendar_id = settings.GOOGLE_CALENDAR_ID  # Your calendar ID
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.scopes
            )
            service = build('calendar', 'v3', credentials=credentials)
            return service
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Calendar: {e}")
            return None
    
    def create_demo_event(self, demo_booking):
        """Create a calendar event with Google Meet link for demo"""
        if not self.service:
            logger.error("Google Calendar service not authenticated")
            return None, None
        
        try:
            # Calculate end time
            end_time = demo_booking.demo_date + timedelta(minutes=demo_booking.duration_minutes)
            
            # Event details
            event_body = {
                'summary': f'Restaurant Voice Assistant Demo - {demo_booking.name}',
                'description': f"""
                Restaurant Voice Assistant Demo Session
                
                Attendee: {demo_booking.name}
                Company: {demo_booking.company or 'N/A'}
                Phone: {demo_booking.phone or 'N/A'}
                
                Message: {demo_booking.message or 'No additional message'}
                
                We'll be demonstrating our AI voice call handling system for restaurants.
                """.strip(),
                'start': {
                    'dateTime': demo_booking.demo_date.isoformat(),
                    'timeZone': demo_booking.timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(), 
                    'timeZone': demo_booking.timezone,
                },
                'attendees': [
                    {'email': demo_booking.email, 'displayName': demo_booking.name},
                    {'email': settings.DEMO_HOST_EMAIL}  # Your email
                ],
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"demo_{demo_booking.id}_{int(datetime.now().timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                    },
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'email', 'minutes': 60},       # 1 hour before
                        {'method': 'popup', 'minutes': 15},       # 15 minutes before
                    ],
                },
                'guestsCanSeeOtherGuests': False,
                'guestsCanInviteOthers': False,
                'sendUpdates': 'all'
            }
            
            # Create the event with Google Meet link
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates='all'
            ).execute()
            
            # Extract Google Meet link and event details
            meet_link = event.get('hangoutLink')
            event_link = event.get('htmlLink')
            event_id = event.get('id')
            
            logger.info(f"Created Google Calendar event: {event_id}")
            
            return {
                'event_id': event_id,
                'meet_link': meet_link,
                'calendar_link': event_link,
                'event': event
            }
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None
    
    def update_event(self, event_id, demo_booking):
        """Update an existing calendar event"""
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update event details
            end_time = demo_booking.demo_date + timedelta(minutes=demo_booking.duration_minutes)
            
            event['summary'] = f'Restaurant Voice Assistant Demo - {demo_booking.name}'
            event['start']['dateTime'] = demo_booking.demo_date.isoformat()
            event['end']['dateTime'] = end_time.isoformat()
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return updated_event
            
        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return None
    
    def cancel_event(self, event_id):
        """Cancel a calendar event"""
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Cancelled calendar event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel calendar event: {e}")
            return False
