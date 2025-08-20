from rest_framework import serializers
from .models import PlanPayment, SubscriptionPlan, CallRecord
from subadmin.models import SubAdminProfile
from datetime import datetime, timedelta
from django.db.models import Count
from authentication.models import CustomUser


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
    

class PlanPaymentSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(write_only=True)  # Accept plan name as input
    plan_id = serializers.PrimaryKeyRelatedField(read_only=True, source='plan')  # Return plan ID in response if needed

    class Meta:
        model = PlanPayment
        fields = ['subadmin', 'plan', 'plan_id', 'payment_status', 'stripe_checkout_id', 'stripe_payment_intent']
        read_only_fields = ['payment_status', 'stripe_checkout_id', 'stripe_payment_intent']

    def validate_plan(self, value):
        try:
            return SubscriptionPlan.objects.get(plan_name=value)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid plan name.")

    def create(self, validated_data):
        plan_instance = validated_data.pop('plan')
        return PlanPayment.objects.create(plan=plan_instance, **validated_data)



class RecentlyOnboardedSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    onboarded_date = serializers.SerializerMethodField()

    class Meta:
        model = SubAdminProfile
        fields = [
            'restaurant_name', 'profile_image', 'restaurant_description',
            'city', 'state', 'plan_name', 'onboarded_date'
        ]

    def get_plan_name(self, obj):
        payment = PlanPayment.objects.filter(
            subadmin=obj.user,  # use related user
            payment_status='PAID'
        ).order_by('-created_at').first()
        return payment.plan.plan_name if payment else None

    def get_onboarded_date(self, obj):
        payment = PlanPayment.objects.filter(
            subadmin=obj.user,  # use related user
            payment_status='PAID'
        ).order_by('created_at').first()
        return payment.created_at.date() if payment else None

    

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'role', 'is_active']


class RestaurantTableSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.first_name', required=False)
    status = serializers.BooleanField(source='user.is_active', required=False)
    email = serializers.EmailField(source='user.email', read_only=True)
    plan_type = serializers.SerializerMethodField()

    class Meta:
        model = SubAdminProfile
        fields = [
            'id',
            'restaurant_name',
            'username',
            'phone_number',
            'plan_type',
            'status',
            'email'
        ]
        extra_kwargs = {
            'restaurant_name': {'required': False},
            'phone_number': {'required': False},
        }

    def get_plan_type(self, obj):
        """Fetch latest paid plan name for this subadmin"""
        payment = (
            PlanPayment.objects
            .filter(subadmin=obj.user, payment_status="PAID")
            .order_by('-created_at')
            .select_related('plan')
            .first()
        )
        return payment.plan.plan_name if payment else None

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        # Update SubAdminProfile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update CustomUser fields
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()

        return instance

class RestaurantStatisticsSerializer(serializers.Serializer):
    total_restaurants = serializers.IntegerField()
    active_restaurants = serializers.IntegerField()
    inactive_restaurants = serializers.IntegerField()
    active_percentage = serializers.FloatField()
    inactive_percentage = serializers.FloatField()
    change_this_month = serializers.IntegerField()


class EarningSerializer(serializers.Serializer):
    period = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    expense = serializers.DecimalField(max_digits=10, decimal_places=2)

class PlanDistributionSerializer(serializers.Serializer):
    plan_name = serializers.CharField()
    count = serializers.IntegerField()



class CallRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRecord
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')



class PlanHistoryPaymentSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.plan_name')
    plan_price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2)
    plan_duration = serializers.CharField(source='plan.duration')
    date_display = serializers.SerializerMethodField()

    class Meta:
        model = PlanPayment
        fields = [
            'plan_name',
            'plan_price',
            'plan_duration',
            'payment_status',
            'date_display'
        ]

    def get_date_display(self, obj):
        return obj.created_at.strftime('%B %d, %Y')  
    

