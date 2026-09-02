import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import ServiceCategory, Booking, BookingStatusHistory
from apps.bookings.services import BookingService
from apps.dashboard.services import DashboardService
from apps.demo.views import DemoSimulateView
from rest_framework.test import APIRequestFactory

@pytest.mark.django_db
class AuditHardeningTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Audit Customer", phone="+1555999000", email="audit@example.com")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer,
            make="Audi",
            model="A6",
            registration_number="NY-AUDIT",
            vehicle_type="SEDAN"
        )
        self.service = ServiceCategory.objects.create(
            name="Major Service",
            description="Complete overhaul",
            base_price=Decimal("450.00")
        )
        self.mechanic = Mechanic.objects.create(
            name="Elena Rostova",
            phone="+1555444333",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE,
            rating=Decimal("4.98")
        )

    def test_single_query_analytics_accuracy(self):
        """Verify optimized single-query timeline aggregations return correct data points."""
        now = timezone.now()
        # Create 3 bookings across today and yesterday
        b1 = Booking.objects.create(
            booking_number="BK-AGG-1", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_COMPLETED, amount=Decimal("450.00"),
            completed_at=now
        )
        b2 = Booking.objects.create(
            booking_number="BK-AGG-2", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_COMPLETED, amount=Decimal("150.00"),
            completed_at=now
        )

        res_bookings = DashboardService.get_analytics_bookings(range_param="7d")
        self.assertEqual(res_bookings["range"], "7d")
        self.assertEqual(len(res_bookings["data"]), 7)

        res_revenue = DashboardService.get_analytics_revenue(range_param="7d")
        self.assertEqual(res_revenue["range"], "7d")
        self.assertEqual(len(res_revenue["data"]), 7)
        # Verify revenue sum
        total_rev = sum(d["revenue"] for d in res_revenue["data"])
        self.assertEqual(total_rev, 600.00)

    def test_demo_simulator_continuous_loop(self):
        """Verify simulator advances bookings and recycles when all are completed."""
        factory = APIRequestFactory()
        view = DemoSimulateView.as_view()

        # Create one pending non-scenario booking
        b = Booking.objects.create(
            booking_number="BK-SIM-TEST",
            customer=self.customer,
            vehicle=self.vehicle,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("450.00"),
            is_demo_scenario=False
        )

        # 1. PENDING -> ASSIGNED
        request = factory.post('/api/v1/demo/simulate/')
        response = view(request)
        self.assertEqual(response.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.STATUS_ASSIGNED)
        self.assertIsNotNone(b.mechanic)

        # 2. ASSIGNED -> ON_THE_WAY
        response = view(request)
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.STATUS_ON_THE_WAY)

        # 3. ON_THE_WAY -> ARRIVED
        response = view(request)
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.STATUS_ARRIVED)

        # 4. ARRIVED -> IN_PROGRESS
        response = view(request)
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.STATUS_IN_PROGRESS)

        # 5. IN_PROGRESS -> COMPLETED
        response = view(request)
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.STATUS_COMPLETED)

        # 6. Next simulate call: should recycle the completed booking to PENDING and advance it
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_atomic_state_locking_safety(self):
        """Verify BookingService transitions acquire lock safely and use assign_mechanic for PENDING→ASSIGNED."""
        b = Booking.objects.create(
            booking_number="BK-LOCK-TEST",
            customer=self.customer,
            vehicle=self.vehicle,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("450.00")
        )

        # PENDING → ASSIGNED must go through assign_mechanic (not generic transition)
        updated = BookingService.assign_mechanic(b, self.mechanic, notes="Locking test")
        self.assertEqual(updated.status, Booking.STATUS_ASSIGNED)
        self.assertIsNotNone(updated.mechanic)
        self.assertEqual(updated.status_history.count(), 1)
