from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import ServiceCategory, Booking
from apps.dashboard.services import DashboardService

class AttentionEngineTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Jane Smith", phone="+1555222333")
        self.vehicle = Vehicle.objects.create(
            customer=self.customer,
            make="Honda",
            model="Civic",
            registration_number="TX-1234",
            vehicle_type="SEDAN"
        )
        self.service = ServiceCategory.objects.create(name="Brakes", base_price=Decimal("280.00"))
        self.mechanic = Mechanic.objects.create(name="Carlos Ramirez", phone="+1555333444", availability_status=Mechanic.AVAILABILITY_AVAILABLE)

    def test_critical_unassigned_rule(self):
        """Test PENDING booking created > 15 min ago triggers CRITICAL."""
        now = timezone.now()
        b = Booking.objects.create(
            booking_number="BK-TEST-CRIT",
            customer=self.customer,
            vehicle=self.vehicle,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("280.00")
        )
        # Set created_at to 18 min ago
        Booking.objects.filter(id=b.id).update(created_at=now - timedelta(minutes=18))

        res = DashboardService.get_attention_items()
        crit_items = [i for i in res["items"] if i["severity"] == "CRITICAL"]
        self.assertEqual(len(crit_items), 1)
        self.assertEqual(crit_items[0]["type"], "UNASSIGNED_BOOKING")
        self.assertEqual(crit_items[0]["entity_id"], b.id)

    def test_high_delayed_dispatch_rule(self):
        """Test ASSIGNED booking assigned > 10 min ago triggers HIGH."""
        now = timezone.now()
        b = Booking.objects.create(
            booking_number="BK-TEST-HIGH",
            customer=self.customer,
            vehicle=self.vehicle,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_ASSIGNED,
            amount=Decimal("280.00"),
            assigned_at=now - timedelta(minutes=14)
        )
        Booking.objects.filter(id=b.id).update(created_at=now - timedelta(minutes=25))

        res = DashboardService.get_attention_items()
        high_items = [i for i in res["items"] if i["severity"] == "HIGH"]
        self.assertEqual(len(high_items), 1)
        self.assertEqual(high_items[0]["type"], "DELAYED_DISPATCH")
        self.assertEqual(high_items[0]["entity_id"], b.id)

    def test_warning_delayed_arrival_rule(self):
        """Test ON_THE_WAY booking with passed ETA triggers WARNING."""
        now = timezone.now()
        b = Booking.objects.create(
            booking_number="BK-TEST-DELAY",
            customer=self.customer,
            vehicle=self.vehicle,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_ON_THE_WAY,
            amount=Decimal("280.00"),
            assigned_at=now - timedelta(minutes=30),
            started_at=now - timedelta(minutes=25),
            estimated_arrival_at=now - timedelta(minutes=5),
            arrived_at=None
        )

        res = DashboardService.get_attention_items()
        warn_items = [i for i in res["items"] if i["type"] == "OVERDUE_ARRIVAL"]
        self.assertEqual(len(warn_items), 1)
        self.assertEqual(warn_items[0]["severity"], "WARNING")
        self.assertEqual(warn_items[0]["entity_id"], b.id)

    def test_warning_overloaded_mechanic_rule(self):
        """Test mechanic with >= 4 active bookings triggers WARNING."""
        now = timezone.now()
        mech = Mechanic.objects.create(name="Overloaded Bob", phone="+1555777888", availability_status=Mechanic.AVAILABILITY_AVAILABLE)

        for i in range(4):
            Booking.objects.create(
                booking_number=f"BK-TEST-LOAD-{i}",
                customer=self.customer,
                vehicle=self.vehicle,
                mechanic=mech,
                service_category=self.service,
                status=Booking.STATUS_ASSIGNED if i % 2 == 0 else Booking.STATUS_IN_PROGRESS,
                amount=Decimal("100.00"),
                assigned_at=now - timedelta(minutes=5)
            )

        res = DashboardService.get_attention_items()
        overload_items = [i for i in res["items"] if i["type"] == "OVERLOADED_MECHANIC"]
        self.assertEqual(len(overload_items), 1)
        self.assertEqual(overload_items[0]["entity_id"], mech.id)
