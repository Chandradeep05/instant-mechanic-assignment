from django.shortcuts import get_object_or_404
from rest_framework import generics, status, views, filters
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.mechanics.models import Mechanic
from .models import Booking, ServiceCategory
from .services import BookingService
from .serializers import (
    BookingListSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    StatusTransitionRequestSerializer,
    AssignMechanicRequestSerializer,
    ServiceCategorySerializer,
)

# Valid status values for filter validation
VALID_BOOKING_STATUSES = {s[0] for s in Booking.STATUS_CHOICES}


@extend_schema(
    tags=['Bookings'],
    summary="List bookings with filters or create a new booking",
    parameters=[
        OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
        OpenApiParameter(name='service_category', description='Filter by service category ID', required=False, type=int),
        OpenApiParameter(name='mechanic', description='Filter by mechanic ID', required=False, type=int),
        OpenApiParameter(name='search', description='Search booking number, customer, vehicle, mechanic', required=False, type=str),
        OpenApiParameter(name='ordering', description='Ordering fields: created_at, -created_at, amount, -amount', required=False, type=str),
    ],
    responses={200: BookingListSerializer, 201: BookingDetailSerializer}
)
class BookingListView(generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'booking_number',
        'customer__name',
        'customer__phone',
        'vehicle__registration_number',
        'vehicle__make',
        'vehicle__model',
        'mechanic__name',
    ]
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookingCreateSerializer
        return BookingListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            BookingDetailSerializer(instance).data,
            status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        """Override list to validate filter params before executing the query."""
        # Validate status filter
        status_param = request.query_params.get('status')
        if status_param and status_param.upper() not in VALID_BOOKING_STATUSES:
            return Response(
                {
                    "error": {
                        "code": "INVALID_STATUS_FILTER",
                        "message": f"Invalid status filter '{status_param}'. Must be one of: {', '.join(sorted(VALID_BOOKING_STATUSES))}",
                        "details": {"valid_statuses": sorted(VALID_BOOKING_STATUSES), "received": status_param}
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate numeric ID filters
        for param_name in ('service_category', 'mechanic'):
            param_value = request.query_params.get(param_name)
            if param_value is not None:
                try:
                    int(param_value)
                except (ValueError, TypeError):
                    return Response(
                        {
                            "error": {
                                "code": "INVALID_FILTER_VALUE",
                                "message": f"Invalid {param_name} filter '{param_value}'. Must be a numeric ID.",
                                "details": {"parameter": param_name, "received": param_value}
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = Booking.objects.select_related('customer', 'vehicle', 'mechanic', 'service_category').all()

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())

        service_param = self.request.query_params.get('service_category')
        if service_param:
            qs = qs.filter(service_category_id=service_param)

        mechanic_param = self.request.query_params.get('mechanic')
        if mechanic_param:
            qs = qs.filter(mechanic_id=mechanic_param)

        return qs


@extend_schema(tags=['Bookings'], summary="Get booking details with full history timeline")
class BookingDetailView(generics.RetrieveAPIView):
    queryset = Booking.objects.select_related(
        'customer', 'vehicle', 'mechanic', 'service_category'
    ).prefetch_related('status_history')
    serializer_class = BookingDetailSerializer


@extend_schema(
    tags=['Bookings'],
    summary="Execute validated status transition",
    request=StatusTransitionRequestSerializer,
    responses={200: BookingDetailSerializer}
)
class BookingTransitionView(views.APIView):
    def post(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.select_related('customer', 'vehicle', 'mechanic', 'service_category'),
            pk=pk
        )
        serializer = StatusTransitionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        updated_booking = BookingService.transition_booking(
            booking=booking,
            new_status=new_status,
            changed_by='OPERATOR',
            notes=notes
        )

        return Response(BookingDetailSerializer(updated_booking).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Bookings'],
    summary="Assign or reassign mechanic to booking",
    request=AssignMechanicRequestSerializer,
    responses={200: BookingDetailSerializer}
)
class BookingAssignView(views.APIView):
    def post(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.select_related('customer', 'vehicle', 'mechanic', 'service_category'),
            pk=pk
        )
        serializer = AssignMechanicRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mechanic_id = serializer.validated_data['mechanic_id']
        notes = serializer.validated_data.get('notes', '')
        mechanic = get_object_or_404(Mechanic, pk=mechanic_id)

        updated_booking = BookingService.assign_mechanic(
            booking=booking,
            mechanic=mechanic,
            changed_by='OPERATOR',
            notes=notes
        )

        return Response(BookingDetailSerializer(updated_booking).data, status=status.HTTP_200_OK)


@extend_schema(tags=['Bookings'], summary="List all service categories")
class ServiceCategoryListView(generics.ListAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    pagination_class = None
