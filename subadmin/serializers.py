from rest_framework import serializers
from .models import BusinessHour, Menu, RestaurantLink, SMSFallbackSettings,MenuItem
from authentication.models import SubAdminProfile

class BusinessHourSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu.name', read_only=True)

    class Meta:
        model = BusinessHour
        fields = [
            'id',
            'subadmin_profile',
            'day',
            'opening_time',
            'closing_time',
            'closed_all_day',
            'menu',        
            'menu_name',    
        ]
  

class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = '__all__'



class MenuItemSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = '__all__'  # keeps all existing fields
        extra_fields = ['menu_name']  # Optional for readability

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['menu_name'] = instance.menu.name  # Ensure it's always included
        return representation



class SubAdminProfileSerializer(serializers.ModelSerializer):
    menus = MenuSerializer(many=True, read_only=True)
    business_hours = BusinessHourSerializer(many=True, read_only=True)

    class Meta:
        model = SubAdminProfile
        fields = [
            'id', 'restaurant_name', 'profile_image', 'phone_number', 'email_address',
            'address', 'city', 'state', 'zip_code', 'country', 'website_url',
            'restaurant_description', 'menus', 'business_hours'
        ]



class PhoneTriggerSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class RestaurantLinkSerializer(serializers.ModelSerializer):
    restaurant_name_display = serializers.CharField(source='restaurant_name.restaurant_name', read_only=True)

    class Meta:
        model = RestaurantLink
        fields = '__all__'
    


class SMSFallbackSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSFallbackSettings
        fields = '__all__'

    

class ProfileImageSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = SubAdminProfile
        fields = ['profile_image', 'profile_image_url']
        extra_kwargs = {
            'profile_image': {'write_only': True}
        }

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            return self.context['request'].build_absolute_uri(obj.profile_image.url)
        return None