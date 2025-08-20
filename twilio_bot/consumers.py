# consumers.py
import json
import io
import logging
import random
import tempfile
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
import speech_recognition as sr
import pydub
from pydub import AudioSegment
from .models import Conversation, Message
import openai
import edge_tts
from .knowledge_base import RestaurantKnowledgeBase  # Import the knowledge base

logger = logging.getLogger(__name__)


class AudioChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.conversation = None
        self.audio_buffer = bytearray()
        self.receiving_audio = False
        self.audio_metadata = {}
        self.tts_voice = "en-US-JennyNeural"  # Edge TTS voice
        self.knowledge_base = RestaurantKnowledgeBase()  # Initialize knowledge base
        
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        await self.accept()
        logger.info(f"WebSocket connected for session {self.session_id}")
        
        try:
            self.conversation = await self.get_or_create_conversation()
            # Send welcome audio message
            await self.send_voice_message("Hello! I'm your restaurant voice assistant specialist. I can help you learn about our AI voice call services for restaurants. What would you like to know?")
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            await self.send_error("Failed to initialize conversation")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected for session {self.session_id} with code {close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                await self.handle_text_message(text_data)
            elif bytes_data:
                await self.handle_binary_message(bytes_data)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(f"Message processing failed: {str(e)}")

    async def handle_text_message(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type in ['text_message', 'text_input']:
                # Still support text input, but respond with voice
                text_content = data.get('content', '')
                ai_response = await self.get_ai_response(text_content)
                await self.send_voice_message(ai_response)
                
            elif message_type in ['audio_start', 'start_audio']:
                self.receiving_audio = True
                self.audio_buffer = bytearray()
                self.audio_metadata = {
                    'size': data.get('size', 0),
                    'mime_type': data.get('mime_type', 'audio/webm'),
                    'format': data.get('format', 'webm')
                }
                logger.info(f"Starting audio reception: {self.audio_metadata}")
                
            elif message_type in ['audio_end', 'end_audio']:
                if self.receiving_audio:
                    await self.process_audio_input()
                self.receiving_audio = False
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error(f"Unsupported message type: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            await self.send_error("Invalid message format")

    async def handle_binary_message(self, bytes_data):
        if self.receiving_audio:
            self.audio_buffer.extend(bytes_data)
            logger.debug(f"Received {len(bytes_data)} bytes of audio data")
        else:
            logger.warning("Received binary data without audio_start")

    async def process_audio_input(self):
        try:
            if len(self.audio_buffer) == 0:
                await self.send_error("No audio data received")
                return
                
            logger.info(f"Processing audio: {len(self.audio_buffer)} bytes")
            
            # Convert audio to text
            transcribed_text = await self.transcribe_audio(bytes(self.audio_buffer))
            
            if transcribed_text:
                # Save user message
                await self.save_message(transcribed_text, is_user=True)
                
                # Send transcription notification (optional)
                await self.send(text_data=json.dumps({
                    'type': 'transcription',
                    'content': transcribed_text
                }))
                
                # Generate AI response using knowledge base
                ai_response = await self.get_ai_response(transcribed_text)
                
                # Save AI response
                await self.save_message(ai_response, is_user=False)
                
                # Convert response to voice and send
                await self.send_voice_message(ai_response)
            else:
                await self.send_voice_message("I'm sorry, I couldn't understand what you said. Could you please try again?")
                
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.send_voice_message("I'm having trouble processing your audio. Please try speaking again.")

    async def transcribe_audio(self, audio_data):
        """Convert audio bytes to text using speech recognition"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                audio = AudioSegment.from_file(temp_file_path, format="webm")
                audio = audio.set_channels(1).set_frame_rate(16000)
                
                wav_path = temp_file_path.replace('.webm', '.wav')
                audio.export(wav_path, format="wav")
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    
                try:
                    text = recognizer.recognize_google(audio_data)
                    logger.info(f"Transcribed: {text}")
                    return text
                except sr.UnknownValueError:
                    logger.warning("Could not understand audio")
                    return None
                except sr.RequestError as e:
                    logger.error(f"Speech recognition error: {e}")
                    try:
                        text = recognizer.recognize_sphinx(audio_data)
                        return text
                    except:
                        return None
                        
            finally:
                try:
                    os.unlink(temp_file_path)
                    if 'wav_path' in locals():
                        os.unlink(wav_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    async def get_ai_response(self, user_input):
        """Generate AI response using database-driven knowledge base"""
        try:
            # Check for demo booking requests first
            demo_response = await self.handle_demo_booking_request(user_input)
            if demo_response:
                return demo_response
        except Exception as e:
            logger.error(f"Demo booking error: {e}")
            return "I'm sorry, I couldn't process your demo booking request. Please try again later."
        
        knowledge_results = await self.knowledge_base.search_knowledge(user_input)
        try:
            # Search knowledge base (now async)
            knowledge_results = await self.knowledge_base.search_knowledge(user_input)
            
            if knowledge_results["confidence"] > 70:
                # High confidence match in knowledge base
                response = self.knowledge_base.format_response(knowledge_results["matches"], user_input)
                logger.info(f"Knowledge base response (confidence: {knowledge_results['confidence']})")
                return response
            
            elif knowledge_results["confidence"] > 40:
                # Medium confidence - use knowledge base response
                response = self.knowledge_base.format_response(knowledge_results["matches"], user_input)
                return response
            
            else:
                # Low confidence - guide user back to relevant topics
                fallback_responses = [
                    "I specialize in restaurant voice assistant services. I can tell you about our AI call handling, pricing plans, features, or implementation process. What interests you most?",
                    "I'm here to help with questions about our restaurant voice call assistant solutions. Would you like to know about pricing, features, or how it works?",
                    "As your restaurant AI specialist, I can explain our voice assistant services, setup process, or benefits for restaurants. What would you like to learn about?",
                ]
                
                return random.choice(fallback_responses)
                
        except Exception as e:
            logger.error(f"AI response error: {e}")
            return "I'm sorry, I'm having trouble accessing my knowledge base right now. Please try asking about our restaurant voice assistant services again."

    async def send_voice_message(self, text):
        """Convert text to speech and send as audio"""
        try:
            # Generate TTS audio
            audio_bytes = await self.text_to_speech(text)
            
            if audio_bytes:
                await self.send(text_data=json.dumps({
                    'type': 'voice_response',
                    'text': text,
                    'has_audio': True
                }))
                
                # Send audio data
                await self.send(bytes_data=audio_bytes)
                
                logger.info(f"Sent voice response: {len(audio_bytes)} bytes")
            else:
                await self.send(text_data=json.dumps({
                    'type': 'text_response',
                    'content': text,
                    'tts_failed': True
                }))
                
        except Exception as e:
            logger.error(f"Voice message error: {e}")
            await self.send_error("Failed to generate voice response")

    async def text_to_speech(self, text):
        """Convert text to speech using Edge TTS"""
        try:
            # Using Edge TTS (free and high quality)
            communicate = edge_tts.Communicate(text, self.tts_voice)
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
            
            await communicate.save(temp_path)
            
            # Read the generated audio file
            with open(temp_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
            
            # Clean up
            os.unlink(temp_path)
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
            # Fallback to gTTS if Edge TTS fails
            try:
                from gtts import gTTS
                tts = gTTS(text=text, lang='en', slow=False)
                
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_path = temp_file.name
                    
                tts.save(temp_path)
                
                with open(temp_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                
                os.unlink(temp_path)
                return audio_bytes
                
            except Exception as fallback_error:
                logger.error(f"Fallback TTS error: {fallback_error}")
                return None

    async def send_error(self, message):
        """Send error message - both text and voice"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
        # Also send as voice
        await self.send_voice_message(f"Error: {message}")

    @database_sync_to_async
    def get_or_create_conversation(self):
        conversation, created = Conversation.objects.get_or_create(
            session_id=self.session_id,
            defaults={'title': 'Restaurant Voice Assistant Chat'}
        )
        return conversation

    @database_sync_to_async
    def save_message(self, content, is_user=True):
        return Message.objects.create(
            conversation=self.conversation,
            text_input=content if is_user else "",
            text_response=content if not is_user else ""
        )
