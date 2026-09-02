import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import ServiceCategory, Booking, BookingStatusHistory
from apps.bookings.services import BookingService
from apps.common.exceptions import (
    InvalidStateTransitionError,
    MechanicUnavailableError,
    BookingTerminalStateError,
)

@pytest.mark.django_db
class BookingTransitionTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="John Doe", phone="+1555123456", email="john@example.com")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer,
            make="Toyota",
            model="Camry",
            registration_number="CA-999ZZ",
            vehicle_type="SEDAN"
        )
        self.service = ServiceCategory.objects.create(
            name="Oil Change",
            description="Synthetic oil change",
            base_price=Decimal("85.00")
        )
        self.mechanic = Mechanic.objects.create(
            name="Marcus Vance",
            phone="+1555987654",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE,
            rating=Decimal("4.95")
        )
        self.offline_mechanic = Mechanic.objects.create(
            name="Offline Mech",
            phone="+1555111222",
            availability_status=Mechanic.AVAILABILITY_OFFLINE,
            rating=Decimal("4.50")
        )
        self.booking = Booking.objects.create(
            booking_number="BK-TEST-001",
            customer=self.customer,
            vehicle=self.vehicle,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("85.00")
        )

    def test_valid_lifecycle_progression(self):
        """Test happy path through entire lifecycle."""
        # 1. PENDING -> ASSIGNED (must use assign_mechanic — generic transition is blocked)
        BookingService.assign_mechanic(self.booking, self.mechanic)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_ASSIGNED)
        self.assertIsNotNone(self.booking.mechanic)

        # 2. ASSIGNED -> ON_THE_WAY
        BookingService.transition_booking(self.booking, Booking.STATUS_ON_THE_WAY)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_ON_THE_WAY)
        self.assertIsNotNone(self.booking.started_at)
        self.assertIsNotNone(self.booking.estimated_arrival_at)

        # 3. ON_THE_WAY -> ARRIVED
        BookingService.transition_booking(self.booking, Booking.STATUS_ARRIVED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_ARRIVED)
        self.assertIsNotNone(self.booking.arrived_at)

        # 4. ARRIVED -> IN_PROGRESS
        BookingService.transition_booking(self.booking, Booking.STATUS_IN_PROGRESS)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_IN_PROGRESS)

        # 5. IN_PROGRESS -> COMPLETED
        BookingService.transition_booking(self.booking, Booking.STATUS_COMPLETED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_COMPLETED)
        self.assertIsNotNone(self.booking.completed_at)

        # Verify status history chain
        history = list(self.booking.status_history.order_by('changed_at'))
        self.assertEqual(len(history), 5)
        self.assertEqual(history[0].previous_status, Booking.STATUS_PENDING)
        self.assertEqual(history[0].new_status, Booking.STATUS_ASSIGNED)
        self.assertEqual(history[-1].new_status, Booking.STATUS_COMPLETED)

    def test_invalid_transitions_rejected(self):
        """Test illegal transitions raise InvalidStateTransitionError and leave DB record unmodified."""
        # PENDING -> COMPLETED is illegal
        with self.assertRaises(InvalidStateTransitionError):
            BookingService.transition_booking(self.booking, Booking.STATUS_COMPLETED)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_PENDING)
        self.assertEqual(self.booking.status_history.count(), 0)

        # Set to COMPLETED with completion timestamp
        self.booking.status = Booking.STATUS_COMPLETED
        self.booking.completed_at = timezone.now()
        self.booking.save()

        # COMPLETED -> ON_THE_WAY is illegal
        with self.assertRaises(InvalidStateTransitionError):
            BookingService.transition_booking(self.booking, Booking.STATUS_ON_THE_WAY)

        # Set to CANCELLED with cancellation timestamp
        self.booking.status = Booking.STATUS_CANCELLED
        self.booking.cancelled_at = timezone.now()
        self.booking.save()

        # CANCELLED -> ASSIGNED is illegal
        with self.assertRaises(InvalidStateTransitionError):
            BookingService.transition_booking(self.booking, Booking.STATUS_ASSIGNED)

    def test_mechanic_assignment(self):
        """Test assigning a mechanic transitions PENDING to ASSIGNED and records history."""
        BookingService.assign_mechanic(self.booking, self.mechanic, notes="Assigned via ops test")
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.mechanic, self.mechanic)
        self.assertEqual(self.booking.status, Booking.STATUS_ASSIGNED)
        self.assertIsNotNone(self.booking.assigned_at)

        history = self.booking.status_history.first()
        self.assertIsNotNone(history)
        self.assertEqual(history.previous_status, Booking.STATUS_PENDING)
        self.assertEqual(history.new_status, Booking.STATUS_ASSIGNED)

    def test_assign_offline_mechanic_fails(self):
        """Test assigning an OFFLINE mechanic raises MechanicUnavailableError."""
        with self.assertRaises(MechanicUnavailableError):
            BookingService.assign_mechanic(self.booking, self.offline_mechanic)

        self.booking.refresh_from_db()
        self.assertIsNone(self.booking.mechanic)
        self.assertEqual(self.booking.status, Booking.STATUS_PENDING)

    def test_assign_terminal_booking_fails(self):
        """Test assigning to COMPLETED or CANCELLED booking raises BookingTerminalStateError."""
        self.booking.status = Booking.STATUS_COMPLETED
        self.booking.completed_at = timezone.now()
        self.booking.save()

        with self.assertRaises(BookingTerminalStateError):
            BookingService.assign_mechanic(self.booking, self.mechanic)
