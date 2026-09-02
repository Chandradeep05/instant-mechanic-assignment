from rest_framework import generics, filters
from django.db.models import Count, Sum, Max, Q, DecimalField
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from .models import Customer
from .serializers import CustomerSerializer

@extend_schema(tags=['Customers'], summary="List customers with lifetime metrics")
class CustomerListView(generics.ListAPIView):
    serializer_class = CustomerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['created_at', 'total_bookings', 'lifetime_value', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        return Customer.objects.annotate(
            vehicle_count=Count('vehicles', distinct=True),
            total_bookings=Count('bookings', distinct=True),
            lifetime_value=Coalesce(
                Sum('bookings__amount', filter=Q(bookings__status='COMPLETED')),
                0.0,
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            last_booking_date=Max('bookings__created_at')
        ).prefetch_related('vehicles')
