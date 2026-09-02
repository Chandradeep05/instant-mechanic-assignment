from decimal import Decimal
from rest_framework import generics, filters
from django.db.models import Count, Sum, Subquery, OuterRef, DecimalField
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from .models import Customer
from .serializers import CustomerSerializer
from apps.bookings.models import Booking

@extend_schema(tags=['Customers'], summary="List customers with lifetime metrics")
class CustomerListView(generics.ListAPIView):
    serializer_class = CustomerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['created_at', 'total_bookings', 'lifetime_value', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        # Correlated Subquery for completed bookings sum:
        # Prevents Cartesian join multiplication when a customer has multiple vehicles.
        completed_bookings_sum = Subquery(
            Booking.objects.filter(
                customer=OuterRef('pk'),
                status=Booking.STATUS_COMPLETED
            ).values('customer').annotate(
                total=Sum('amount')
            ).values('total')[:1],
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )

        last_booking_date_subquery = Subquery(
            Booking.objects.filter(
                customer=OuterRef('pk')
            ).order_by('-created_at').values('created_at')[:1]
        )

        return Customer.objects.annotate(
            vehicle_count=Count('vehicles', distinct=True),
            total_bookings=Count('bookings', distinct=True),
            lifetime_value=Coalesce(
                completed_bookings_sum,
                Decimal('0.00'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            last_booking_date=last_booking_date_subquery
        ).prefetch_related('vehicles')
