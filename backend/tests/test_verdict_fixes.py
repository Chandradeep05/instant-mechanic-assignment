"""
Targeted tests for every P0/P1 finding from both external audits.
These tests verify the fixes, not just that the code runs without errors.
"""
import pytest
from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, APIClient

from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import ServiceCategory, Booking, BookingStatusHistory
from apps.bookings.services import BookingService, ALLOWED_TRANSITIONS, MAX_CONCURRENT_JOBS
from apps.common.exceptions import InvalidStateTransitionError, MechanicUnavailableError
from apps.dashboard.services import DashboardService


@pytest.mark.django_db
class StateMachineInvariantTests(TestCase):
    """P0-1: Verify ASSIGNED + mechanic=NULL is impossible via every code path."""

    def setUp(self):
        self.customer = Customer.objects.create(name="Test Customer", phone="+91 9876543210", email="test@gmail.com")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, make="Maruti Suzuki", model="Swift",
            registration_number="DL-01-AB-1234", vehicle_type="HATCHBACK"
        )
        self.service = ServiceCategory.objects.create(
            name="Engine Diagnostic", description="Full scan", base_price=Decimal("2500.00")
        )
        self.mechanic = Mechanic.objects.create(
            name="Rajesh Kumar", phone="+91 9876543211",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE, rating=Decimal("4.95")
        )

    def test_assigned_not_in_pending_transitions(self):
        """ASSIGNED must NOT be in ALLOWED_TRANSITIONS[PENDING].
        Assignment is a business operation through assign_mechanic(), not a generic transition."""
        allowed = ALLOWED_TRANSITIONS.get(Booking.STATUS_PENDING, [])
        self.assertNotIn(
            Booking.STATUS_ASSIGNED, allowed,
            "ASSIGNED must not be reachable from PENDING via generic transition — use assign_mechanic()"
        )

    def test_transition_to_assigned_without_mechanic_rejected(self):
        """POST /transition/ with status=ASSIGNED on a mechanic-less booking must fail.
        Even if somehow the transition map is changed, the guard must catch it."""
        booking = Booking.objects.create(
            booking_number="BK-INV-001", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("2500.00"), mechanic=None
        )
        with self.assertRaises(InvalidStateTransitionError):
            BookingService.transition_booking(booking, Booking.STATUS_ASSIGNED)

    def test_transition_api_rejects_assigned_on_pending(self):
        """API-level test: POST /bookings/{id}/transition/ {"status": "ASSIGNED"} → 409."""
        booking = Booking.objects.create(
            booking_number="BK-API-001", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("2500.00"), mechanic=None
        )
        client = APIClient()
        response = client.post(
            f'/api/v1/bookings/{booking.id}/transition/',
            {"status": "ASSIGNED"},
            format='json'
        )
        self.assertEqual(response.status_code, 409)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_PENDING, "Booking should remain PENDING")
        self.assertIsNone(booking.mechanic, "Mechanic should remain NULL")

    def test_assign_mechanic_creates_valid_assigned_state(self):
        """The ONLY way to reach ASSIGNED is through assign_mechanic() with a valid mechanic."""
        booking = Booking.objects.create(
            booking_number="BK-VALID-001", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("2500.00"), mechanic=None
        )
        updated = BookingService.assign_mechanic(booking, self.mechanic)
        self.assertEqual(updated.status, Booking.STATUS_ASSIGNED)
        self.assertIsNotNone(updated.mechanic, "ASSIGNED must have mechanic IS NOT NULL")
        self.assertEqual(updated.mechanic.id, self.mechanic.id)

    def test_full_lifecycle_always_has_mechanic_when_active(self):
        """Walk the complete lifecycle PENDING → ASSIGNED → ... → COMPLETED.
        Verify mechanic is never NULL during active states."""
        booking = Booking.objects.create(
            booking_number="BK-LIFE-001", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("2500.00")
        )
        # Assign mechanic (PENDING → ASSIGNED)
        booking = BookingService.assign_mechanic(booking, self.mechanic)
        self.assertIsNotNone(booking.mechanic)

        # Walk through remaining states
        for next_status in [Booking.STATUS_ON_THE_WAY, Booking.STATUS_ARRIVED,
                            Booking.STATUS_IN_PROGRESS, Booking.STATUS_COMPLETED]:
            booking = BookingService.transition_booking(booking, next_status)
            if next_status != Booking.STATUS_COMPLETED:
                self.assertIsNotNone(booking.mechanic_id,
                                     f"Mechanic must not be NULL in {next_status}")


@pytest.mark.django_db
class MechanicCapacityTests(TestCase):
    """P1-3: Verify mechanic capacity limit enforcement."""

    def setUp(self):
        self.customer = Customer.objects.create(name="Capacity Test", phone="+91 9876500000", email="cap@gmail.com")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, make="Hyundai", model="Creta",
            registration_number="MH-01-CD-5678", vehicle_type="SUV"
        )
        self.service = ServiceCategory.objects.create(
            name="Capacity Test Service", description="Test", base_price=Decimal("3000.00")
        )
        self.mechanic = Mechanic.objects.create(
            name="Busy Mechanic", phone="+91 9876500001",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE, rating=Decimal("4.90")
        )

    def test_mechanic_capacity_limit_enforced(self):
        """Assigning more than MAX_CONCURRENT_JOBS to a single mechanic must fail."""
        # Fill up the mechanic to capacity
        for i in range(MAX_CONCURRENT_JOBS):
            booking = Booking.objects.create(
                booking_number=f"BK-CAP-{i}", customer=self.customer, vehicle=self.vehicle,
                service_category=self.service, status=Booking.STATUS_PENDING,
                amount=Decimal("3000.00")
            )
            BookingService.assign_mechanic(booking, self.mechanic)

        # The next assignment must fail
        overflow_booking = Booking.objects.create(
            booking_number="BK-CAP-OVERFLOW", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("3000.00")
        )
        with self.assertRaises(MechanicUnavailableError) as ctx:
            BookingService.assign_mechanic(overflow_booking, self.mechanic)

        self.assertIn(str(MAX_CONCURRENT_JOBS), str(ctx.exception.detail))

    def test_completed_jobs_dont_count_toward_capacity(self):
        """Completed jobs should not count against the mechanic's active capacity."""
        # Create MAX_CONCURRENT_JOBS bookings, complete them all
        for i in range(MAX_CONCURRENT_JOBS):
            booking = Booking.objects.create(
                booking_number=f"BK-DONE-{i}", customer=self.customer, vehicle=self.vehicle,
                service_category=self.service, status=Booking.STATUS_PENDING,
                amount=Decimal("3000.00")
            )
            booking = BookingService.assign_mechanic(booking, self.mechanic)
            booking = BookingService.transition_booking(booking, Booking.STATUS_ON_THE_WAY)
            booking = BookingService.transition_booking(booking, Booking.STATUS_ARRIVED)
            booking = BookingService.transition_booking(booking, Booking.STATUS_IN_PROGRESS)
            booking = BookingService.transition_booking(booking, Booking.STATUS_COMPLETED)

        # Now a new assignment should succeed
        new_booking = Booking.objects.create(
            booking_number="BK-AFTER-DONE", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("3000.00")
        )
        result = BookingService.assign_mechanic(new_booking, self.mechanic)
        self.assertEqual(result.status, Booking.STATUS_ASSIGNED)


@pytest.mark.django_db
class BusyMechanicsKPITests(TestCase):
    """P1-4: busy_mechanics must include BREAK/OFFLINE mechanics with active jobs."""

    def setUp(self):
        self.customer = Customer.objects.create(name="KPI Test", phone="+91 9876500002", email="kpi@gmail.com")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, make="Tata", model="Nexon",
            registration_number="KA-01-EF-9012", vehicle_type="SUV"
        )
        self.service = ServiceCategory.objects.create(
            name="KPI Test Service", description="Test", base_price=Decimal("1500.00")
        )

    def test_busy_mechanics_includes_break_mechanics_with_jobs(self):
        """A mechanic on BREAK with an active booking should count as busy."""
        mech = Mechanic.objects.create(
            name="Break Mechanic", phone="+91 9876500003",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE, rating=Decimal("4.80")
        )
        # Create and assign a booking
        booking = Booking.objects.create(
            booking_number="BK-BREAK-001", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("1500.00")
        )
        BookingService.assign_mechanic(booking, mech)

        # Now put the mechanic on BREAK
        mech.availability_status = Mechanic.AVAILABILITY_BREAK
        mech.save()

        kpis = DashboardService.get_overview_kpis()
        self.assertGreaterEqual(
            kpis['busy_mechanics'], 1,
            "A BREAK mechanic with an active job must count as busy"
        )


@pytest.mark.django_db
class AnalyticsRangeValidationTests(TestCase):
    """P1-5: Invalid analytics range must return 400, not silently default to 7d."""

    def test_invalid_bookings_range_returns_400(self):
        client = APIClient()
        response = client.get('/api/v1/analytics/bookings/', {'range': 'garbage'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('INVALID_RANGE', str(response.data))

    def test_invalid_revenue_range_returns_400(self):
        client = APIClient()
        response = client.get('/api/v1/analytics/revenue/', {'range': 'banana'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('INVALID_RANGE', str(response.data))

    def test_valid_bookings_ranges_accepted(self):
        client = APIClient()
        for valid_range in ['24h', '7d', '30d']:
            response = client.get('/api/v1/analytics/bookings/', {'range': valid_range})
            self.assertEqual(response.status_code, 200, f"Range '{valid_range}' should be accepted")

    def test_valid_revenue_ranges_accepted(self):
        client = APIClient()
        for valid_range in ['7d', '30d']:
            response = client.get('/api/v1/analytics/revenue/', {'range': valid_range})
            self.assertEqual(response.status_code, 200, f"Range '{valid_range}' should be accepted")


@pytest.mark.django_db
class BookingFilterValidationTests(TestCase):
    """P2-5: Invalid filter params must return 400."""

    def test_invalid_status_filter_returns_400(self):
        client = APIClient()
        response = client.get('/api/v1/bookings/', {'status': 'DOES_NOT_EXIST'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('INVALID_STATUS_FILTER', str(response.data))

    def test_non_numeric_service_category_returns_400(self):
        client = APIClient()
        response = client.get('/api/v1/bookings/', {'service_category': 'banana'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('INVALID_FILTER_VALUE', str(response.data))

    def test_non_numeric_mechanic_returns_400(self):
        client = APIClient()
        response = client.get('/api/v1/bookings/', {'mechanic': 'not-a-number'})
        self.assertEqual(response.status_code, 400)

    def test_valid_status_filter_accepted(self):
        client = APIClient()
        response = client.get('/api/v1/bookings/', {'status': 'PENDING'})
        self.assertEqual(response.status_code, 200)


@pytest.mark.django_db
class DemoSimulatorCapacityTests(TestCase):
    """P1-Simulator: Simulator must skip overloaded mechanics (active_jobs >= 4) and pick an available mechanic with capacity."""

    def setUp(self):
        self.customer = Customer.objects.create(name="Sim Customer", phone="+91 9876543299", email="sim@gmail.com")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, make="Honda", model="City",
            registration_number="DL-03-CD-9999", vehicle_type="SEDAN"
        )
        self.service = ServiceCategory.objects.create(
            name="Sim Service", description="Test", base_price=Decimal("2000.00")
        )
        # Overloaded mechanic (4 active jobs)
        self.overloaded_mech = Mechanic.objects.create(
            name="Overloaded Mech", phone="+91 9876543201",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE, rating=Decimal("4.85")
        )
        for i in range(4):
            b = Booking.objects.create(
                booking_number=f"BK-OVER-{i}", customer=self.customer, vehicle=self.vehicle,
                service_category=self.service, status=Booking.STATUS_PENDING,
                amount=Decimal("2000.00"), is_demo_scenario=True
            )
            BookingService.assign_mechanic(b, self.overloaded_mech)

        # Free mechanic (0 active jobs)
        self.free_mech = Mechanic.objects.create(
            name="Free Mech", phone="+91 9876543202",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE, rating=Decimal("4.90")
        )

    def test_simulator_selects_free_mechanic_when_first_is_overloaded(self):
        """When the first available mechanic is at capacity (4 jobs), the simulator must assign to the free mechanic."""
        pending_booking = Booking.objects.create(
            booking_number="BK-SIM-PENDING-01", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING,
            amount=Decimal("2000.00"), is_demo_scenario=False
        )
        client = APIClient()
        response = client.post('/api/v1/demo/simulate/')
        self.assertEqual(response.status_code, 200)

        pending_booking.refresh_from_db()
        self.assertEqual(pending_booking.status, Booking.STATUS_ASSIGNED)
        self.assertEqual(pending_booking.mechanic.id, self.free_mech.id, "Simulator should pick the mechanic with capacity")

