from typing import Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from apps.bookings.models import Booking, ServiceCategory
from apps.mechanics.models import Mechanic
from apps.bookings.services import BookingService
from apps.bookings.serializers import BookingDetailSerializer
from apps.customers.models import Customer, Vehicle
from django.utils import timezone
from decimal import Decimal
import random


from django.db import transaction
from django.db.models import Count, Q

@extend_schema(tags=['Demo'], summary="Simulate advancing one eligible booking in the demo pool")
class DemoSimulateView(APIView):
    def post(self, request):
        with transaction.atomic():
            # Acquire row lock without nullable outer join (prevents PostgreSQL FOR UPDATE error)
            # and use skip_locked=True so concurrent simulator requests select different bookings.
            booking = (
                Booking.objects
                .select_for_update(skip_locked=True)
                .filter(
                    is_demo_scenario=False,
                    status__in=[
                        Booking.STATUS_PENDING,
                        Booking.STATUS_ASSIGNED,
                        Booking.STATUS_ON_THE_WAY,
                        Booking.STATUS_ARRIVED,
                        Booking.STATUS_IN_PROGRESS,
                    ]
                )
                .order_by('created_at')
                .first()
            )

            # If all active bookings are exhausted, create a NEW demo booking instead of
            # mutating COMPLETED -> PENDING (which bypasses the state machine).
            if not booking:
                booking = _create_fresh_demo_booking()
                if not booking:
                    return Response(
                        {"message": "No demo data available. Run seed_data first: python manage.py seed_data"},
                        status=status.HTTP_200_OK
                    )
                # Re-select row with lock in this transaction
                booking = Booking.objects.select_for_update().get(id=booking.id)

            # Populate FK fields via separate non-locking fetch for downstream logic
            booking = Booking.objects.select_related(
                'customer', 'vehicle', 'mechanic', 'service_category'
            ).get(id=booking.id)

            current_status = booking.status
            next_status_map = {
                Booking.STATUS_PENDING: Booking.STATUS_ASSIGNED,
                Booking.STATUS_ASSIGNED: Booking.STATUS_ON_THE_WAY,
                Booking.STATUS_ON_THE_WAY: Booking.STATUS_ARRIVED,
                Booking.STATUS_ARRIVED: Booking.STATUS_IN_PROGRESS,
                Booking.STATUS_IN_PROGRESS: Booking.STATUS_COMPLETED,
            }
            target_status = next_status_map.get(current_status)

            if not target_status:
                return Response(
                    {"message": f"Booking is in unrecognized state '{current_status}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # PENDING -> ASSIGNED always requires a mechanic via assign_mechanic()
            # We NEVER call transition_booking() directly for PENDING -> ASSIGNED.
            # Domain invariant: ASSIGNED implies mechanic IS NOT NULL.
            if current_status == Booking.STATUS_PENDING:
                active_statuses = [
                    Booking.STATUS_ASSIGNED,
                    Booking.STATUS_ON_THE_WAY,
                    Booking.STATUS_ARRIVED,
                    Booking.STATUS_IN_PROGRESS,
                ]
                available_mechanic = (
                    Mechanic.objects.filter(
                        availability_status=Mechanic.AVAILABILITY_AVAILABLE
                    ).annotate(
                        active_job_count=Count('bookings', filter=Q(bookings__status__in=active_statuses))
                    ).filter(active_job_count__lt=4).order_by('active_job_count', 'id').first()
                )
                if not available_mechanic:
                    return Response(
                        {
                            "message": "Cannot advance booking: no AVAILABLE mechanic with capacity found. "
                                       "All available mechanics have reached max concurrent jobs (4) or are OFFLINE/BREAK."
                        },
                        status=status.HTTP_200_OK
                    )

                booking = BookingService.assign_mechanic(
                    booking=booking,
                    mechanic=available_mechanic,
                    changed_by='SIMULATOR',
                    notes='Auto-assigned by LiveOps Simulator',
                    already_locked=True
                )
            else:
                booking = BookingService.transition_booking(
                    booking=booking,
                    new_status=target_status,
                    changed_by='SIMULATOR',
                    notes=f'Simulated progression {current_status} → {target_status}',
                    already_locked=True
                )

        return Response({
            "message": f"Advanced booking {booking.booking_number}: {current_status} → {booking.status}.",
            "booking": BookingDetailSerializer(booking).data
        }, status=status.HTTP_200_OK)


def _create_fresh_demo_booking() -> Optional[Booking]:
    """
    Creates a fresh PENDING booking from existing seed data for continuous simulation.
    Never recycles COMPLETED bookings to avoid bypassing the state machine.
    """
    import uuid

    # Vehicle-first: guarantees the booking always pairs a customer with their own vehicle.
    # Random customer-first with fallback could pair customer A with vehicle owned by customer B.
    vehicle = Vehicle.objects.select_related('customer').order_by('?').first()
    if not vehicle or not vehicle.customer_id:
        return None
    customer = vehicle.customer

    service = ServiceCategory.objects.order_by('?').first()
    if not service:
        return None

    price_mult = Decimal(str(round(random.uniform(0.90, 1.25), 2)))
    amount = round(service.base_price * price_mult, 2)

    booking_number = f"BK-SIM-{uuid.uuid4().hex[:8].upper()}"

    return Booking.objects.create(
        booking_number=booking_number,
        customer=customer,
        vehicle=vehicle,
        mechanic=None,
        service_category=service,
        status=Booking.STATUS_PENDING,
        amount=amount,
        is_demo_scenario=False,
    )
