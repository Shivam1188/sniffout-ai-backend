# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json

class KnowledgeCategory(models.Model):
    """Categories for organizing knowledge base content"""
    CATEGORY_TYPES = [
        ('services', 'Services'),
        ('pricing', 'Pricing'),
        ('features', 'Features'),
        ('implementation', 'Implementation'),
        ('faq', 'FAQ'),
        ('restaurant_types', 'Restaurant Types'),
        ('technical', 'Technical Specifications'),
        ('success_stories', 'Success Stories'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True, help_text="Brief description of this category")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Knowledge Categories"
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"

class KnowledgeItem(models.Model):
    """Individual knowledge base items"""
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Main content/answer")
    keywords = models.TextField(
        help_text="Comma-separated keywords for matching queries",
        blank=True
    )
    confidence_boost = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        help_text="Boost confidence score by this amount (-50 to +50)"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'order', 'title']
    
    def __str__(self):
        return f"{self.category.name}: {self.title}"
    
    def get_keywords_list(self):
        """Return keywords as a list"""
        if self.keywords:
            return [kw.strip().lower() for kw in self.keywords.split(',') if kw.strip()]
        return []

class ServiceFeature(models.Model):
    """Features of the voice assistant service"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(
        KnowledgeCategory, 
        on_delete=models.CASCADE, 
        limit_choices_to={'category_type': 'features'},
        related_name='features'
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class PricingPlan(models.Model):
    """Pricing plans for the service"""
    PLAN_TYPES = [
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.CharField(max_length=50, help_text="e.g., $99/month, Custom pricing")
    description = models.TextField(blank=True)
    features = models.TextField(help_text="One feature per line")
    call_limit = models.CharField(max_length=100, blank=True, help_text="e.g., Up to 500 calls/month")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.price}"
    
    def get_features_list(self):
        """Return features as a list"""
        return [f.strip() for f in self.features.split('\n') if f.strip()]

class RestaurantType(models.Model):
    """Types of restaurants that use the service"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    solution_details = models.TextField(
        blank=True,
        help_text="Specific solution details for this restaurant type"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class FAQ(models.Model):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=300)
    answer = models.TextField()
    keywords = models.TextField(
        help_text="Comma-separated keywords for matching",
        blank=True
    )
    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.CASCADE,
        limit_choices_to={'category_type': 'faq'},
        related_name='faqs'
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'question']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return self.question
    
    def get_keywords_list(self):
        """Return keywords as a list"""
        if self.keywords:
            return [kw.strip().lower() for kw in self.keywords.split(',') if kw.strip()]
        return []

class SuccessStory(models.Model):
    """Customer success stories"""
    restaurant_name = models.CharField(max_length=100)
    restaurant_type = models.ForeignKey(
        RestaurantType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    story = models.TextField()
    metrics = models.TextField(
        blank=True,
        help_text="Key metrics/improvements (one per line)"
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'restaurant_name']
        verbose_name_plural = "Success Stories"
    
    def __str__(self):
        return f"{self.restaurant_name} Success Story"
    
    def get_metrics_list(self):
        """Return metrics as a list"""
        if self.metrics:
            return [m.strip() for m in self.metrics.split('\n') if m.strip()]
        return []

class TechnicalSpec(models.Model):
    """Technical specifications"""
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.CASCADE,
        limit_choices_to={'category_type': 'technical'},
        related_name='tech_specs'
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Technical Specification"
    
    def __str__(self):
        return f"{self.name}: {self.value}"


class Conversation(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, default="Chat Session")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    text_input = models.TextField(blank=True)
    text_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']


import uuid

class DemoBooking(models.Model):
    DEMO_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'), 
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=100, blank=True, null=True)
    demo_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)  # Demo duration
    timezone = models.CharField(max_length=50, default='UTC')
    status = models.CharField(max_length=20, choices=DEMO_STATUS_CHOICES, default='scheduled')
    
    # Google Calendar integration fields
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    google_meet_link = models.URLField(blank=True, null=True)
    google_calendar_link = models.URLField(blank=True, null=True)
    
    # Additional info
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Demo - {self.name} - {self.demo_date}"

class DemoAvailability(models.Model):
    """Define available time slots for demos"""
    day_of_week = models.IntegerField(choices=[
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time}"