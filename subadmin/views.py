from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from .models import BusinessHour, Menu, RestaurantLink, SMSFallbackSettings, MenuItem
from django.core.mail import send_mail
from .serializers import BusinessHourSerializer,MenuSerializer, SubAdminProfileSerializer, PhoneTriggerSerializer, RestaurantLinkSerializer, SMSFallbackSettingsSerializer,MenuItemSerializer,ProfileImageSerializer
from rest_framework import permissions, status
from authentication.models import SubAdminProfile, CustomUser
from superadmin.permissions import IsSuperUserOrReadOnly
from superadmin.models import CallRecord
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
import requests
from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Avg
from rest_framework.decorators import action
from authentication.utils import success_response, error_response


error_message = "Already exist ."


class BusinessHourViewSet(viewsets.ModelViewSet):
    queryset = BusinessHour.objects.all()
    serializer_class = BusinessHourSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        subadmin_id = self.request.query_params.get('subadmin_id')
        if subadmin_id:
            return self.queryset.filter(subadmin_profile__id=subadmin_id)
        return self.queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return success_response(
                message="Business hour created successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        else:
            return error_response(
                message="Validation failed.",
                errors=error_message,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return success_response(
                message="Business hour updated successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        else:
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return success_response(
                message="Business hour deleted successfully.",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return error_response(
                message="Failed to delete business hour.",
                errors=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Menu deleted successfully"},
            status=status.HTTP_200_OK
        )


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]



class AllRestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubAdminProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Superadmin check (based on role)
        if user.role == 'admin':
            return SubAdminProfile.objects.all()

        # Subadmin check: has SubAdminProfile
        elif hasattr(user, 'subadmin_profile'):
            return SubAdminProfile.objects.filter(user=user)

        # All other roles (e.g. users) get nothing
        return SubAdminProfile.objects.none()
    

@api_view(['POST'])
def get_menu_by_twilio_number(request):
    print("Request data:", request.data)
    print("Request headers:", dict(request.headers))

    # Step 1: Extract Twilio number (callee number)
    twilio_number = (
        request.data.get('to') or
        request.POST.get('to') or
        request.data.get('callee', {}).get('phoneNumber') or
        request.headers.get('X-Vapi-Call-Phone-Number-To') or
        request.headers.get('To') or
        request.data.get('call', {}).get('phoneNumberTo')
    )

    # Step 2: Fallbacks for older/alternate keys
    if not twilio_number or str(twilio_number).startswith("{{"):
        twilio_number = (
            request.headers.get('X-Twilio-To') or
            request.data.get('phoneNumber') or
            request.data.get('restaurant_phone') or
            request.data.get('number') or
            request.data.get('from') or
            request.data.get('caller')
        )

    print("Final phone number extracted:", twilio_number)

    if not twilio_number:
        return Response({'error': 'Missing phone number in payload.'}, status=400)

    # Step 3: Normalize the phone number
    normalized_number = ''.join(filter(str.isdigit, twilio_number))

    phone_variations = [
        f"+{normalized_number}",
        normalized_number.lstrip('91'),  # Remove India code
        f"+91{normalized_number}" if not normalized_number.startswith('91') else f"+{normalized_number}",
        f"+1{normalized_number}" if not normalized_number.startswith('1') else f"+{normalized_number}"
    ]

    # Step 4: Match to SubAdmin by phone
    subadmin = None
    for phone in phone_variations:
        try:
            subadmin = SubAdminProfile.objects.get(phone_number=phone)
            break
        except SubAdminProfile.DoesNotExist:
            continue

    if not subadmin:
        return Response({
            'error': f'No restaurant found for phone number: {twilio_number}',
            'tried_variations': phone_variations
        }, status=404)

    # Step 5: Get active menu
    active_menus = Menu.objects.filter(subadmin_profile=subadmin, is_active=True)
    if not active_menus.exists():
        return Response({'error': 'No active menu found for this restaurant.'}, status=404)

    menu_list = [
        {
            "name": menu.name,
            "description": menu.description
        }
        for menu in active_menus
    ]

    return Response({
        "restaurant_name": subadmin.restaurant_name,
        "phone_number": twilio_number,
        "menus": menu_list
    })


@api_view(['POST'])
def handle_incoming_call(request):
    twilio_number = request.data.get('to') or request.data.get('callee', {}).get('phoneNumber')
    caller = request.data.get('from') or request.data.get('caller', {}).get('phoneNumber')
    print(caller, "======here is caller ================")

    if not twilio_number or not caller:
        return Response({"error": "Missing 'to' or 'from' number"}, status=400)

    # Step 1: Call local menu API
    menu_response = requests.post(
        "https://3e33db4654fa.ngrok-free.app/api/subadmin/get-menu-by-twilio/",
        json={"to": twilio_number},
        headers={"Content-Type": "application/json"}
    )

    if menu_response.status_code != 200:
        print(f"Menu API Error: {menu_response.status_code} - {menu_response.text}")
        return Response({
            "error": "Failed to get menu",
            "details": menu_response.text
        }, status=500)

    menu_data = menu_response.json()
    print(menu_data, "=====menu data ======")

    # Step 2: Trigger Vapi Assistant - Fixed endpoint and payload
    vapi_payload = {
        "assistant": {
            "model": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a helpful restaurant assistant for {menu_data.get('restaurant_name', 'our restaurant')}. Here are our available menus: {menu_data.get('menus', [])}"
                    }
                ]
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM"  # Replace with your preferred voice ID
            }
        },
        "phoneNumberId": twilio_number,  # Your Vapi phone number ID
        "customer": {
            "number": caller
        }
    }

    # Alternative payload structure if you're using a pre-configured assistant
    # vapi_payload = {
    #     "assistantId": "your-assistant-id-here",  # Replace with your assistant ID
    #     "phoneNumberId": "your-phone-number-id",  # Replace with your Vapi phone number ID
    #     "customer": {
    #         "number": caller
    #     },
    #     "assistantOverrides": {
    #         "variableValues": {
    #             "all_restaurant": menu_data
    #         }
    #     }
    # }

    try:
        vapi_response = requests.post(
            "https://api.vapi.ai/call",  # Try this endpoint instead
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=vapi_payload,
            timeout=30  # Add timeout
        )
        
        print(f"Vapi Response Status: {vapi_response.status_code}")
        print(f"Vapi Response: {vapi_response.text}")
        
        if vapi_response.status_code not in [200, 201]:
            # If first endpoint fails, try the alternative
            vapi_response_alt = requests.post(
                "https://api.vapi.ai/v1/call",  # Alternative endpoint
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=vapi_payload,
                timeout=30
            )
            
            print(f"Alternative Vapi Response Status: {vapi_response_alt.status_code}")
            print(f"Alternative Vapi Response: {vapi_response_alt.text}")
            
            if vapi_response_alt.status_code in [200, 201]:
                vapi_response = vapi_response_alt
            else:
                raise requests.RequestException(f"Both endpoints failed: {vapi_response.status_code}, {vapi_response_alt.status_code}")

    except requests.RequestException as e:
        print(f"Vapi API Request Error: {str(e)}")
        return Response({
            "error": "Vapi call failed",
            "details": str(e)
        }, status=500)

    if vapi_response.status_code not in [200, 201]:
        print(f"Vapi API Error: {vapi_response.status_code} - {vapi_response.text}")
        return Response({
            "error": "Vapi call failed",
            "details": vapi_response.text,
            "status_code": vapi_response.status_code
        }, status=500)

    return Response({
        "status": "Vapi assistant started successfully",
        "data": vapi_response.json(),
        "menu_data": menu_data
    })


# @api_view(['POST'])
# def trigger_email_by_phone(request):
#     serializer = PhoneTriggerSerializer(data=request.data)
    
#     if serializer.is_valid():
#         phone_number = serializer.validated_data['phone_number']
#         print("Received phone number:", phone_number)

#         try:
#             subadmin = SubAdminProfile.objects.get(phone_number=phone_number)
#             print("Found SubAdmin:", subadmin.email_address)
#         except SubAdminProfile.DoesNotExist:
#             print("No subadmin found for phone:", phone_number)
#             return Response({'error': 'Phone number not found.'}, status=status.HTTP_404_NOT_FOUND)

#         try:
#             send_mail(
#                 subject='Trigger Notification',
#                 message='This is an automated email triggered by your phone number.',
#                 from_email='testampli2023@gmail.com',
#                 recipient_list=['sonu@yopmail.com'],
#                 fail_silently=False,
#             )
#             print("Email sent successfully.")
#         except Exception as e:
#             print("Error while sending email:", str(e))
#             return Response({"error": f"Email failed: {str(e)}"}, status=500)

#         return Response({'message': f'Email sent to {subadmin.email_address}'}, status=200)

#     print("Serializer invalid:", serializer.errors)
#     return Response(serializer.errors, status=400)


@api_view(['POST'])
def sending_email(request):
    phone_number = request.data.get('phone_number')
    order = request.data.get('order')

    try:
        subadmin = SubAdminProfile.objects.get(phone_number=phone_number)
        send_mail(
            subject='New Order Received',
            message=f"Order Details:\n\n{order}",
            from_email='testampli2023@gmail.com',
            recipient_list=['sonu@yopmail.com'],
            fail_silently=False,
        )
        return Response({'message': 'Order email sent successfully.'})
    except SubAdminProfile.DoesNotExist:
        return Response({'error': 'Subadmin not found for this phone.'}, status=404)
    except Exception as e:
        return Response({'error': f'Failed to send email: {str(e)}'}, status=500)




class RestaurantLinkViewSet(viewsets.ModelViewSet):
    queryset = RestaurantLink.objects.all()
    serializer_class = RestaurantLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only allow subadmins to see their own links.
        Superadmins can see all.
        """
        user = self.request.user
        if user.is_superuser:
            return RestaurantLink.objects.all()
        return RestaurantLink.objects.filter(subadmin=user)

    def create(self, request, *args, **kwargs):
        if RestaurantLink.objects.filter(subadmin=request.user).exists():
            return Response(
                {"error": "You can only add one restaurant link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_superuser and instance.subadmin != request.user:
            return Response(
                {"error": "You can only delete your own restaurant link."},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    


class SMSFallbackSettingsViewSet(viewsets.ModelViewSet):
    queryset = SMSFallbackSettings.objects.all()
    serializer_class = SMSFallbackSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

####======================for Subadmin Dashboard========================####


class TodaysCallsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            subadmin = SubAdminProfile.objects.get(user=user)
        except SubAdminProfile.DoesNotExist:
            return Response({'error': 'SubAdmin profile not found.'}, status=404)

        today = now().date()
        yesterday = today - timedelta(days=1)

        # Today's and yesterday's call counts
        todays_calls = CallRecord.objects.filter(
            restaurant=subadmin,
            created_at__date=today
        ).count()

        yesterdays_calls = CallRecord.objects.filter(
            restaurant=subadmin,
            created_at__date=yesterday
        ).count()

        if yesterdays_calls > 0:
            percentage_change = ((todays_calls - yesterdays_calls) / yesterdays_calls) * 100
        else:
            percentage_change = 100 if todays_calls > 0 else 0

        return Response({
            "todays_calls": todays_calls,
            "percentage_change": round(percentage_change, 2)
        })
    


class MissedCallsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            subadmin = SubAdminProfile.objects.get(user=user)
        except SubAdminProfile.DoesNotExist:
            return Response({'error': 'SubAdmin profile not found.'}, status=404)

        today = now().date()
        yesterday = today - timedelta(days=1)

        # Missed = status='failed'
        todays_missed = CallRecord.objects.filter(
            restaurant=subadmin,
            created_at__date=today,
            status='failed'
        ).count()

        yesterdays_missed = CallRecord.objects.filter(
            restaurant=subadmin,
            created_at__date=yesterday,
            status='failed'
        ).count()

        if yesterdays_missed > 0:
            percentage_change = ((todays_missed - yesterdays_missed) / yesterdays_missed) * 100
        else:
            percentage_change = 100 if todays_missed > 0 else 0

        return Response({
            "missed_calls": todays_missed,
            "percentage_change": round(percentage_change, 2)
        })
    


class AverageCallDurationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            subadmin = SubAdminProfile.objects.get(user=user)
        except SubAdminProfile.DoesNotExist:
            return Response({'error': 'SubAdmin profile not found.'}, status=404)

        today = now().date()
        yesterday = today - timedelta(days=1)

        # Get average durations in seconds
        today_avg = CallRecord.objects.filter(
            restaurant=subadmin,
            created_at__date=today,
            duration__isnull=False
        ).aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0

        yesterday_avg = CallRecord.objects.filter(
            restaurant=subadmin,
            created_at__date=yesterday,
            duration__isnull=False
        ).aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0

        # Percentage change
        if yesterday_avg > 0:
            percentage_change = ((today_avg - yesterday_avg) / yesterday_avg) * 100
        else:
            percentage_change = 0 if today_avg == 0 else 100

        # Format duration as mm:ss
        def format_duration(seconds):
            minutes = int(seconds) // 60
            sec = int(seconds) % 60
            return f"{minutes}:{sec:02}"

        return Response({
            "average_duration": format_duration(today_avg),
            "percentage_change": round(percentage_change, 2)
        })
    


class RecentCallsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            subadmin = SubAdminProfile.objects.get(user=user)
        except SubAdminProfile.DoesNotExist:
            return Response({'error': 'SubAdmin profile not found.'}, status=404)

        recent_calls = CallRecord.objects.filter(
            restaurant=subadmin
        ).order_by('-created_at')[:4]

        data = []
        for call in recent_calls:
            data.append({
                "call_sid": call.call_sid,
                "status": call.status,
                "duration": call.duration,
                "caller_number": call.caller_number,  # <-- included here
                "created_at": call.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return Response({"recent_calls": data})
    



class ProfileViewSet(viewsets.GenericViewSet):
    queryset = SubAdminProfile.objects.all()
    serializer_class = ProfileImageSerializer

    def get_object(self):
        user_id = self.kwargs.get('pk')  
        user = get_object_or_404(CustomUser, id=user_id)
        return get_object_or_404(SubAdminProfile, user=user)
    
    def retrieve(self, request, pk=None):
        """GET /api/subadmin/profile/<pk>/ to get profile details"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put', 'patch'], url_path='update-profile-image')
    def update_profile_image(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'profile_image_url': serializer.get_profile_image_url(instance),
            'message': 'Profile image updated successfully'
        }, status=status.HTTP_200_OK)