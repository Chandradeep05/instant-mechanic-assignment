from rest_framework import serializers
from .models import Customer, Vehicle

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'make', 'model', 'registration_number', 'vehicle_type']

class CustomerSerializer(serializers.ModelSerializer):
    vehicles = VehicleSerializer(many=True, read_only=True)
    vehicle_count = serializers.IntegerField(read_only=True, default=0)
    total_bookings = serializers.IntegerField(read_only=True, default=0)
    lifetime_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=0.0)
    last_booking_date = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'created_at',
            'vehicles', 'vehicle_count', 'total_bookings', 'lifetime_value', 'last_booking_date'
        ]
