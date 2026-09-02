from rest_framework import serializers
from apps.customers.serializers import CustomerSerializer, VehicleSerializer
from apps.mechanics.serializers import MechanicSerializer
from .models import Booking, BookingStatusHistory, ServiceCategory

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'base_price']

class BookingStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatusHistory
        fields = ['id', 'previous_status', 'new_status', 'changed_at', 'changed_by', 'notes']

class BookingListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service_category.name', read_only=True)
    mechanic_name = serializers.CharField(source='mechanic.name', read_only=True, allow_null=True)
    mechanic_id = serializers.IntegerField(source='mechanic.id', read_only=True, allow_null=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'status', 'amount', 'created_at', 'updated_at',
            'customer_name', 'customer_phone', 'vehicle_info',
            'service_name', 'mechanic_name', 'mechanic_id',
            'assigned_at', 'started_at', 'estimated_arrival_at', 'arrived_at', 'completed_at', 'cancelled_at'
        ]

    def get_vehicle_info(self, obj):
        if obj.vehicle:
            return f"{obj.vehicle.make} {obj.vehicle.model} ({obj.vehicle.registration_number})"
        return ""

class BookingDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    mechanic = MechanicSerializer(read_only=True)
    service_category = ServiceCategorySerializer(read_only=True)
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'status', 'amount', 'is_demo_scenario',
            'created_at', 'updated_at', 'assigned_at', 'started_at', 'estimated_arrival_at',
            'arrived_at', 'completed_at', 'cancelled_at',
            'customer', 'vehicle', 'mechanic', 'service_category',
            'status_history', 'allowed_transitions'
        ]

    def get_allowed_transitions(self, obj):
        from .services import ALLOWED_TRANSITIONS
        return ALLOWED_TRANSITIONS.get(obj.status, [])

class StatusTransitionRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Booking.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

class AssignMechanicRequestSerializer(serializers.Serializer):
    mechanic_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')
