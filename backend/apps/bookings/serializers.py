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


FORBIDDEN_CREATE_FIELDS = {
    "status",
    "mechanic",
    "assigned_at",
    "started_at",
    "estimated_arrival_at",
    "arrived_at",
    "completed_at",
    "cancelled_at",
}


class BookingCreateSerializer(serializers.ModelSerializer):
    booking_number = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = Booking
        fields = [
            'booking_number',
            'customer',
            'vehicle',
            'service_category',
            'amount',
        ]

    def validate(self, attrs):
        # 1. Explicitly reject forbidden mutation fields during creation
        forbidden = FORBIDDEN_CREATE_FIELDS.intersection(self.initial_data.keys())
        if forbidden:
            raise serializers.ValidationError(
                {field: f"Field '{field}' cannot be set during booking creation. Use domain service endpoints." for field in sorted(forbidden)}
            )

        # 2. Enforce customer-vehicle ownership invariant
        customer = attrs['customer']
        vehicle = attrs['vehicle']
        if vehicle.customer_id != customer.id:
            raise serializers.ValidationError({
                "vehicle": f"Vehicle '{vehicle.registration_number}' does not belong to customer '{customer.name}'."
            })

        return attrs

    def create(self, validated_data):
        import uuid
        from django.utils import timezone
        from django.db import transaction
        from .services import publish_booking_event, get_booking_event_payload

        service = validated_data['service_category']
        amount = validated_data.get('amount')
        if amount is None:
            amount = service.base_price

        booking_number = validated_data.get('booking_number')
        with transaction.atomic():
            if not booking_number:
                # Generate unique booking number with collision retry
                for _ in range(5):
                    candidate = f"BK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                    if not Booking.objects.filter(booking_number=candidate).exists():
                        booking_number = candidate
                        break
                if not booking_number:
                    booking_number = f"BK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

            booking = Booking.objects.create(
                booking_number=booking_number,
                customer=validated_data['customer'],
                vehicle=validated_data['vehicle'],
                service_category=service,
                amount=amount,
                status=Booking.STATUS_PENDING,
                mechanic=None,
            )

            BookingStatusHistory.objects.create(
                booking=booking,
                previous_status='CREATED',
                new_status=Booking.STATUS_PENDING,
                changed_by='OPERATOR',
                notes='Initial booking creation'
            )

            payload = get_booking_event_payload(booking)
            transaction.on_commit(lambda: publish_booking_event("booking.created", payload))

        return booking
