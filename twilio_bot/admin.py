from django.contrib import admin
from .models import Conversation, Message , KnowledgeCategory, KnowledgeItem, ServiceFeature, PricingPlan, RestaurantType, FAQ, SuccessStory, TechnicalSpec,DemoBooking, DemoAvailability


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'is_active', 'order', 'items_count']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    def items_count(self, obj):
        return obj.items.filter(is_active=True).count()
    items_count.short_description = 'Active Items'

@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_active', 'confidence_boost', 'order']
    list_filter = ['category', 'is_active', 'category__category_type']
    search_fields = ['title', 'content', 'keywords']
    ordering = ['category', 'order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'title', 'content')
        }),
        ('Matching & Display', {
            'fields': ('keywords', 'confidence_boost', 'order', 'is_active')
        }),
    )

@admin.register(ServiceFeature)
class ServiceFeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']

@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'is_active', 'is_featured', 'order']
    list_filter = ['plan_type', 'is_active', 'is_featured']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Plan Details', {
            'fields': ('name', 'plan_type', 'price', 'description')
        }),
        ('Features & Limits', {
            'fields': ('features', 'call_limit')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'is_featured', 'order')
        }),
    )

@admin.register(RestaurantType)
class RestaurantTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'is_active', 'view_count', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer', 'keywords']
    ordering = ['order', 'question']
    readonly_fields = ['view_count']

@admin.register(SuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ['restaurant_name', 'restaurant_type', 'is_active', 'is_featured', 'order']
    list_filter = ['restaurant_type', 'is_active', 'is_featured']
    search_fields = ['restaurant_name', 'story']
    ordering = ['order', 'restaurant_name']

@admin.register(TechnicalSpec)
class TechnicalSpecAdmin(admin.ModelAdmin):
    list_display = ['name', 'value', 'category', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'value', 'description']
    ordering = ['order', 'name']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'title', 'created_at', 'messages_count']
    search_fields = ['session_id', 'title']
    readonly_fields = ['created_at', 'updated_at']
    
    def messages_count(self, obj):
        return obj.messages.count()
    messages_count.short_description = 'Messages'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'has_input', 'has_response']
    search_fields = ['conversation__session_id', 'text_input', 'text_response']
    
    def has_input(self, obj):
        return bool(obj.text_input)
    has_input.boolean = True
    has_input.short_description = 'Has Input'
    
    def has_response(self, obj):
        return bool(obj.text_response)
    has_response.boolean = True
    has_response.short_description = 'Has Response'



@admin.register(DemoBooking)
class DemoBookingAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'email', 'phone']
    ordering = ['-created_at']
    



@admin.register(DemoAvailability)
class DemoAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['day_of_week', 'start_time']
    search_fields = ['day_of_week', 'start_time']
    ordering = ['day_of_week', 'start_time']
    