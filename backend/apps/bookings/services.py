from datetime import timedelta
import logging
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.common.exceptions import (
    InvalidStateTransitionError,
    MechanicUnavailableError,
    BookingTerminalStateError,
)
from apps.mechanics.models import Mechanic
from .models import Booking, BookingStatusHistory

logger = logging.getLogger(__name__)

# Maximum concurrent active jobs a single mechanic can handle.
# Prevents unlimited assignment and makes the overload policy explicit.
MAX_CONCURRENT_JOBS = 4

# ──────────────────────────────────────────────────────────────
# STATE MACHINE — Allowed Transitions
# ──────────────────────────────────────────────────────────────
# IMPORTANT: PENDING → ASSIGNED is NOT here.
# Assignment is a business operation that requires mechanic selection.
# It must go through assign_mechanic(), never through the generic
# transition endpoint. This prevents ASSIGNED + mechanic=NULL.
# ──────────────────────────────────────────────────────────────
ALLOWED_TRANSITIONS = {
    Booking.STATUS_PENDING: [Booking.STATUS_CANCELLED],
    Booking.STATUS_ASSIGNED: [Booking.STATUS_ON_THE_WAY, Booking.STATUS_CANCELLED],
    Booking.STATUS_ON_THE_WAY: [Booking.STATUS_ARRIVED, Booking.STATUS_CANCELLED],
    Booking.STATUS_ARRIVED: [Booking.STATUS_IN_PROGRESS, Booking.STATUS_CANCELLED],
    Booking.STATUS_IN_PROGRESS: [Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED],
    Booking.STATUS_COMPLETED: [],
    Booking.STATUS_CANCELLED: [],
}


def publish_booking_event(event_type: str, data: dict):
    """
    Broadcasts a real-time event to the LiveOps Channels group.
    Called post-commit via transaction.on_commit().
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "liveops_channel",
                {
                    "type": "broadcast.event",
                    "event": event_type,
                    "data": data,
                }
            )
    except Exception as e:
        logger.warning(f"Failed to broadcast websocket event {event_type}: {e}")


def get_booking_event_payload(booking: Booking) -> dict:
    """
    Helper to serialize booking summary for WebSocket broadcast.
    Uses the real updated_at field (auto_now) rather than fabricating a timestamp.
    """
    return {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "status": booking.status,
        "amount": str(booking.amount),
        "customer_name": booking.customer.name if booking.customer else "",
        "mechanic_id": booking.mechanic.id if booking.mechanic else None,
        "mechanic_name": booking.mechanic.name if booking.mechanic else None,
        "service_name": booking.service_category.name if booking.service_category else "",
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
        "updated_at": booking.updated_at.isoformat() if booking.updated_at else None,
    }


class BookingService:
    @staticmethod
    def transition_booking(booking: Booking, new_status: str, changed_by: str = 'OPERATOR', notes: str = '') -> Booking:
        """
        Executes a validated status transition inside an atomic transaction with row locking.

        Domain invariant enforced here:
        - Active statuses (ASSIGNED, ON_THE_WAY, ARRIVED, IN_PROGRESS) require mechanic IS NOT NULL.
        - PENDING → ASSIGNED is NOT in ALLOWED_TRANSITIONS — use assign_mechanic() instead.
        """
        now = timezone.now()

        with transaction.atomic():
            # Acquire row lock to prevent concurrent transition race conditions.
            # select_related is intentionally excluded: PostgreSQL raises
            # "FOR UPDATE cannot be applied to the nullable side of an outer join"
            # when mechanic (nullable FK) is included in select_for_update().
            locked_booking = Booking.objects.select_for_update().get(id=booking.id)
            # Populate FK fields via a separate non-locking fetch so the rest of
            # the method can access booking.customer, booking.mechanic, etc.
            locked_booking = Booking.objects.select_related(
                'customer', 'vehicle', 'mechanic', 'service_category'
            ).get(id=locked_booking.id)

            allowed = ALLOWED_TRANSITIONS.get(locked_booking.status, [])
            if new_status not in allowed:
                raise InvalidStateTransitionError(
                    message=f"Cannot transition booking {locked_booking.booking_number} from '{locked_booking.status}' to '{new_status}'. Allowed: {allowed}",
                    details={"current_status": locked_booking.status, "requested_status": new_status, "allowed": allowed}
                )

            # Enforce mechanic-required invariant for active statuses
            MECHANIC_REQUIRED_STATUSES = [
                Booking.STATUS_ASSIGNED,
                Booking.STATUS_ON_THE_WAY,
                Booking.STATUS_ARRIVED,
                Booking.STATUS_IN_PROGRESS,
            ]
            if new_status in MECHANIC_REQUIRED_STATUSES and not locked_booking.mechanic_id:
                raise InvalidStateTransitionError(
                    message=f"Cannot transition to '{new_status}': booking has no assigned mechanic. Use the /assign/ endpoint first.",
                    details={"current_status": locked_booking.status, "requested_status": new_status}
                )

            previous_status = locked_booking.status
            locked_booking.status = new_status

            if new_status == Booking.STATUS_ON_THE_WAY:
                if not locked_booking.started_at:
                    locked_booking.started_at = now
                if not locked_booking.estimated_arrival_at:
                    locked_booking.estimated_arrival_at = now + timedelta(minutes=25)
            elif new_status == Booking.STATUS_ARRIVED:
                if not locked_booking.arrived_at:
                    locked_booking.arrived_at = now
            elif new_status == Booking.STATUS_COMPLETED:
                if not locked_booking.completed_at:
                    locked_booking.completed_at = now
            elif new_status == Booking.STATUS_CANCELLED:
                if not locked_booking.cancelled_at:
                    locked_booking.cancelled_at = now

            locked_booking.save()

            BookingStatusHistory.objects.create(
                booking=locked_booking,
                previous_status=previous_status,
                new_status=new_status,
                changed_by=changed_by,
                notes=notes or f"Status transitioned from {previous_status} to {new_status}"
            )

            # Capture payload inside the transaction, then register on_commit
            event_payload = get_booking_event_payload(locked_booking)
            transaction.on_commit(lambda: publish_booking_event("booking.updated", event_payload))

        return locked_booking

    @staticmethod
    def assign_mechanic(booking: Booking, mechanic: Mechanic, changed_by: str = 'OPERATOR', notes: str = '') -> Booking:
        """
        Assigns or reassigns a mechanic to a booking. Only allowed for PENDING or ASSIGNED bookings.
        Reassignment after travel has begun (ON_THE_WAY+) is rejected to preserve domain integrity.

        Domain invariants enforced:
        - ASSIGNED/ON_THE_WAY/ARRIVED/IN_PROGRESS => mechanic IS NOT NULL
        - Only AVAILABILITY_AVAILABLE mechanics can be assigned
        - Mechanic cannot exceed MAX_CONCURRENT_JOBS active bookings
        """
        now = timezone.now()

        with transaction.atomic():
            # Lock the booking row only — same reason as transition_booking.
            locked_booking = Booking.objects.select_for_update().get(id=booking.id)
            locked_booking = Booking.objects.select_related(
                'customer', 'vehicle', 'mechanic', 'service_category'
            ).get(id=locked_booking.id)

            # Terminal states reject assignment
            if locked_booking.status in [Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED]:
                raise BookingTerminalStateError(
                    message=f"Cannot assign mechanic to booking {locked_booking.booking_number} in terminal state '{locked_booking.status}'."
                )

            # Reject reassignment once travel has started (preserves status history semantics)
            if locked_booking.status not in [Booking.STATUS_PENDING, Booking.STATUS_ASSIGNED]:
                raise InvalidStateTransitionError(
                    message=f"Cannot reassign mechanic once booking is in '{locked_booking.status}' state. Reassignment is only allowed for PENDING or ASSIGNED bookings.",
                    details={"current_status": locked_booking.status, "allowed_for_reassignment": ["PENDING", "ASSIGNED"]}
                )

            # Re-verify mechanic availability inside the lock — only AVAILABLE mechanics can be assigned
            locked_mechanic = Mechanic.objects.select_for_update().get(id=mechanic.id)
            if locked_mechanic.availability_status != Mechanic.AVAILABILITY_AVAILABLE:
                raise MechanicUnavailableError(
                    message=f"Cannot assign mechanic '{locked_mechanic.name}': status is '{locked_mechanic.availability_status}'. Only AVAILABLE mechanics can be assigned."
                )

            # Enforce capacity limit — prevent overloading beyond MAX_CONCURRENT_JOBS
            active_statuses = [
                Booking.STATUS_ASSIGNED,
                Booking.STATUS_ON_THE_WAY,
                Booking.STATUS_ARRIVED,
                Booking.STATUS_IN_PROGRESS,
            ]
            current_active_jobs = Booking.objects.filter(
                mechanic=locked_mechanic,
                status__in=active_statuses
            ).exclude(id=locked_booking.id).count()

            if current_active_jobs >= MAX_CONCURRENT_JOBS:
                raise MechanicUnavailableError(
                    message=f"Mechanic '{locked_mechanic.name}' already has {current_active_jobs} active jobs (limit: {MAX_CONCURRENT_JOBS}). Cannot assign more.",
                    details={
                        "mechanic_id": locked_mechanic.id,
                        "active_jobs": current_active_jobs,
                        "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
                    }
                )

            previous_status = locked_booking.status
            locked_booking.mechanic = locked_mechanic

            if locked_booking.status == Booking.STATUS_PENDING:
                locked_booking.status = Booking.STATUS_ASSIGNED
                locked_booking.assigned_at = now

            locked_booking.save()

            BookingStatusHistory.objects.create(
                booking=locked_booking,
                previous_status=previous_status,
                new_status=locked_booking.status,
                changed_by=changed_by,
                notes=notes or f"Assigned to {locked_mechanic.name}"
            )

            event_payload = get_booking_event_payload(locked_booking)
            transaction.on_commit(lambda: publish_booking_event("booking.assigned", event_payload))

        return locked_booking
