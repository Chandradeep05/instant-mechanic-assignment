from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import ServiceCategory, Booking
from apps.dashboard.services import DashboardService

class DashboardKPITestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Alice", phone="+1555000111")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer,
            make="Ford",
            model="F-150",
            registration_number="FL-777",
            vehicle_type="TRUCK"
        )
        self.service = ServiceCategory.objects.create(name="Tires", base_price=Decimal("150.00"))

        self.mech_avail = Mechanic.objects.create(name="Available Joe", phone="123", availability_status=Mechanic.AVAILABILITY_AVAILABLE)
        self.mech_busy = Mechanic.objects.create(name="Busy Jane", phone="456", availability_status=Mechanic.AVAILABILITY_AVAILABLE)
        self.mech_offline = Mechanic.objects.create(name="Offline Dan", phone="789", availability_status=Mechanic.AVAILABILITY_OFFLINE)

    def test_total_revenue_calculation(self):
        """Test total revenue only sums COMPLETED bookings."""
        now = timezone.now()
        # Completed booking $200
        b1 = Booking.objects.create(
            booking_number="BK-REV-1", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_COMPLETED, amount=Decimal("200.00"),
            completed_at=now
        )
        # Completed booking $150
        b2 = Booking.objects.create(
            booking_number="BK-REV-2", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_COMPLETED, amount=Decimal("150.00"),
            completed_at=now
        )
        # Pending booking $300 (should NOT be in revenue)
        Booking.objects.create(
            booking_number="BK-REV-3", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_PENDING, amount=Decimal("300.00")
        )
        # Cancelled booking $500 (should NOT be in revenue)
        Booking.objects.create(
            booking_number="BK-REV-4", customer=self.customer, vehicle=self.vehicle,
            service_category=self.service, status=Booking.STATUS_CANCELLED, amount=Decimal("500.00"),
            cancelled_at=now
        )

        kpis = DashboardService.get_overview_kpis()
        self.assertEqual(kpis["total_revenue"], 350.00)
        self.assertEqual(kpis["today_revenue"], 350.00)
        self.assertEqual(kpis["completed_bookings"], 2)
        self.assertEqual(kpis["pending_bookings"], 1)
        self.assertEqual(kpis["cancelled_bookings"], 1)

    def test_active_and_available_mechanics(self):
        """Test active mechanics excludes OFFLINE, and available mechanics requires 0 active bookings."""
        # Assign 1 active job to Busy Jane
        Booking.objects.create(
            booking_number="BK-JOB-1", customer=self.customer, vehicle=self.vehicle,
            mechanic=self.mech_busy, service_category=self.service,
            status=Booking.STATUS_ASSIGNED, amount=Decimal("150.00")
        )

        kpis = DashboardService.get_overview_kpis()
        self.assertEqual(kpis["active_mechanics"], 2) # Joe and Jane (Dan is OFFLINE)
        self.assertEqual(kpis["available_mechanics"], 1) # Only Joe has 0 active jobs
        self.assertEqual(kpis["busy_mechanics"], 1) # Jane has 1 active job
