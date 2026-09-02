from rest_framework import serializers
from .models import Mechanic

class MechanicBookingMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    booking_number = serializers.CharField()
    status = serializers.CharField()
    service_name = serializers.CharField(source='service_category.name', default='')
    customer_name = serializers.CharField(source='customer.name', default='')

class MechanicSerializer(serializers.ModelSerializer):
    active_jobs_count = serializers.SerializerMethodField()
    total_jobs_completed = serializers.SerializerMethodField()
    operational_status = serializers.SerializerMethodField()
    primary_booking = serializers.SerializerMethodField()
    workload_badge = serializers.SerializerMethodField()

    class Meta:
        model = Mechanic
        fields = [
            'id', 'name', 'phone', 'availability_status', 'rating', 'created_at',
            'active_jobs_count', 'total_jobs_completed', 'operational_status',
            'primary_booking', 'workload_badge'
        ]

    def get_active_jobs_count(self, obj):
        if hasattr(obj, '_active_jobs_count'):
            return obj._active_jobs_count
        if hasattr(obj, '_prefetched_active_bookings'):
            return len(obj._prefetched_active_bookings)
        return obj.bookings.filter(status__in=['ASSIGNED', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS']).count()

    def get_total_jobs_completed(self, obj):
        if hasattr(obj, '_total_jobs_completed'):
            return obj._total_jobs_completed
        return obj.bookings.filter(status='COMPLETED').count()

    def get_operational_status(self, obj):
        if obj.availability_status == Mechanic.AVAILABILITY_OFFLINE:
            return 'OFFLINE'
        if obj.availability_status == Mechanic.AVAILABILITY_BREAK:
            return 'BREAK'
        
        # Check active bookings using prefetched cache
        active_bookings = getattr(obj, '_prefetched_active_bookings', None)
        if active_bookings is None:
            active_bookings = list(obj.bookings.filter(status__in=['ASSIGNED', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS']))

        if any(b.status == 'IN_PROGRESS' for b in active_bookings):
            return 'ON_JOB'
        elif any(b.status in ['ASSIGNED', 'ON_THE_WAY', 'ARRIVED'] for b in active_bookings):
            return 'ASSIGNED'
        else:
            return 'AVAILABLE'

    def get_primary_booking(self, obj):
        active_bookings = getattr(obj, '_prefetched_active_bookings', None)
        if active_bookings is None:
            active_bookings = list(obj.bookings.filter(
                status__in=['ASSIGNED', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS']
            ).order_by('created_at').select_related('service_category', 'customer'))

        if active_bookings:
            oldest = active_bookings[0]
            return {
                'id': oldest.id,
                'booking_number': oldest.booking_number,
                'status': oldest.status,
                'service_name': oldest.service_category.name if oldest.service_category else '',
                'customer_name': oldest.customer.name if oldest.customer else '',
            }
        return None

    def get_workload_badge(self, obj):
        count = self.get_active_jobs_count(obj)
        if count >= 4:
            return 'OVERLOADED'
        elif count >= 2:
            return 'BUSY'
        elif count == 1:
            return 'ACTIVE'
        else:
            return 'IDLE'
