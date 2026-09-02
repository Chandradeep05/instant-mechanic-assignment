from rest_framework import generics, filters
from django.db.models import Prefetch, Count, Q
from drf_spectacular.utils import extend_schema
from .models import Mechanic
from .serializers import MechanicSerializer
from apps.bookings.models import Booking

ACTIVE_STATUSES = [
    Booking.STATUS_ASSIGNED,
    Booking.STATUS_ON_THE_WAY,
    Booking.STATUS_ARRIVED,
    Booking.STATUS_IN_PROGRESS
]

@extend_schema(tags=['Mechanics'], summary="List all mechanics with operational status and active jobs")
class MechanicListView(generics.ListAPIView):
    serializer_class = MechanicSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone']
    ordering_fields = ['name', 'rating', 'availability_status']
    ordering = ['name']

    def get_queryset(self):
        active_bookings_qs = Booking.objects.filter(
            status__in=ACTIVE_STATUSES
        ).select_related('service_category', 'customer').order_by('created_at')

        return Mechanic.objects.annotate(
            _active_jobs_count=Count('bookings', filter=Q(bookings__status__in=ACTIVE_STATUSES)),
            _total_jobs_completed=Count('bookings', filter=Q(bookings__status=Booking.STATUS_COMPLETED))
        ).prefetch_related(
            Prefetch('bookings', queryset=active_bookings_qs, to_attr='_prefetched_active_bookings')
        )

@extend_schema(tags=['Mechanics'], summary="Retrieve single mechanic details")
class MechanicDetailView(generics.RetrieveAPIView):
    serializer_class = MechanicSerializer

    def get_queryset(self):
        active_bookings_qs = Booking.objects.filter(
            status__in=ACTIVE_STATUSES
        ).select_related('service_category', 'customer').order_by('created_at')

        return Mechanic.objects.annotate(
            _active_jobs_count=Count('bookings', filter=Q(bookings__status__in=ACTIVE_STATUSES)),
            _total_jobs_completed=Count('bookings', filter=Q(bookings__status=Booking.STATUS_COMPLETED))
        ).prefetch_related(
            Prefetch('bookings', queryset=active_bookings_qs, to_attr='_prefetched_active_bookings')
        )
