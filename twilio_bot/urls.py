# urls.py (in your twilio_bot app)
from django.urls import path
from .views import MakeCallView, VoiceAssistantView, DebugView,get_menu_by_twilio_number
from . import views

urlpatterns = [
    path('make-call/', MakeCallView.as_view(), name='make-call'),
    path('voice-assistant/', VoiceAssistantView.as_view(), name='voice-assistant'),
    path('debug/', DebugView.as_view(), name='debug'),
    path('get-menu-by-twilio/', get_menu_by_twilio_number, name='get_menu_by_twilio'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/<str:session_id>/', views.chat_view, name='chat_with_session'),
    
    # API endpoints
    path('api/conversations/', views.ConversationListCreateView.as_view(), name='conversation-list'),
    path('api/conversations/create/', views.create_conversation, name='create-conversation'),
    path('api/conversations/<str:session_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('api/conversations/<str:session_id>/messages/create/', views.save_message, name='save-message'),
    
    # Debug endpoints
    path('api/health/', views.health_check, name='health-check'),
    path('api/debug/conversations/', views.debug_conversations, name='debug-conversations'),
    path('schedule-demo/', views.schedule_demo, name='schedule_demo'),
    path('book-demo/', views.book_demo, name='book_demo'),
    path('demo/<uuid:demo_id>/', views.demo_details, name='demo_details'),
    path('cancel-demo/<uuid:demo_id>/', views.cancel_demo, name='cancel_demo'),
]