import pytest
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import Booking, BookingStatusHistory, ServiceCategory
from apps.customers.views import CustomerListView
from apps.dashboard.services import DashboardService
from apps.demo.views import DemoSimulateView
from django.core.management import call_command


@pytest.mark.django_db
class FinalHardeningTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Ramesh Gupta",
            phone="+91 9811223344",
            email="ramesh.gupta@example.com"
        )
        self.vehicle_1 = Vehicle.objects.create(
            customer=self.customer,
            make="Maruti Suzuki",
            model="Brezza",
            registration_number="DL-01-XX-1001",
            vehicle_type="SUV"
        )
        self.vehicle_2 = Vehicle.objects.create(
            customer=self.customer,
            make="Hyundai",
            model="i20",
            registration_number="DL-01-YY-2002",
            vehicle_type="HATCHBACK"
        )
        self.service = ServiceCategory.objects.create(
            name="Full Synthetic Oil & Filter Service",
            description="Premium synthetic service",
            base_price=Decimal("1800.00")
        )
        self.mechanic = Mechanic.objects.create(
            name="Amit Verma",
            phone="+91 9822334455",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE,
            rating=Decimal("4.90")
        )
        self.client = APIClient()

    def test_customer_lifetime_value_no_cartesian_multiplication(self):
        """
        P0-1 Fix Verification:
        Customer has 2 vehicles and 2 completed bookings (₹1,000 + ₹2,000 = ₹3,000).
        Cartesian join product must NOT multiply lifetime_value to ₹6,000.
        """
        Booking.objects.create(
            booking_number="BK-LTV-001",
            customer=self.customer,
            vehicle=self.vehicle_1,
            service_category=self.service,
            status=Booking.STATUS_COMPLETED,
            amount=Decimal("1000.00"),
            completed_at=timezone.now()
        )
        Booking.objects.create(
            booking_number="BK-LTV-002",
            customer=self.customer,
            vehicle=self.vehicle_2,
            service_category=self.service,
            status=Booking.STATUS_COMPLETED,
            amount=Decimal("2000.00"),
            completed_at=timezone.now()
        )

        qs = CustomerListView().get_queryset()
        annotated_customer = qs.get(id=self.customer.id)

        self.assertEqual(
            Decimal(str(annotated_customer.lifetime_value)),
            Decimal("3000.00"),
            f"Expected lifetime_value to be exactly 3000.00, got {annotated_customer.lifetime_value}"
        )
        self.assertEqual(annotated_customer.vehicle_count, 2)
        self.assertEqual(annotated_customer.total_bookings, 2)

    def test_create_booking_api_success(self):
        """
        P1 Fix Verification:
        POST /api/v1/bookings/ creates a new booking in PENDING state with mechanic=None,
        defaulting amount to the service category's base price.
        """
        payload = {
            "customer": self.customer.id,
            "vehicle": self.vehicle_1.id,
            "service_category": self.service.id,
        }
        res = self.client.post('/api/v1/bookings/', payload, format='json')
        self.assertEqual(res.status_code, 201)

        data = res.data
        self.assertEqual(data['status'], Booking.STATUS_PENDING)
        self.assertIsNone(data['mechanic'])
        self.assertEqual(Decimal(str(data['amount'])), self.service.base_price)
        self.assertTrue(data['booking_number'].startswith("BK-"))

        # Verify initial history record was recorded
        booking = Booking.objects.get(id=data['id'])
        history = booking.status_history.first()
        self.assertIsNotNone(history)
        self.assertEqual(history.previous_status, 'CREATED')
        self.assertEqual(history.new_status, Booking.STATUS_PENDING)

    def test_create_booking_rejects_forbidden_fields(self):
        """
        P1 Fix Verification:
        Directly attempting to set status or mechanic on creation must be rejected.
        """
        payload = {
            "customer": self.customer.id,
            "vehicle": self.vehicle_1.id,
            "service_category": self.service.id,
            "status": "COMPLETED",
            "mechanic": self.mechanic.id,
        }
        res = self.client.post('/api/v1/bookings/', payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("mechanic", str(res.data))
        self.assertIn("status", str(res.data))

    def test_create_booking_rejects_mismatched_vehicle_owner(self):
        """
        P1 Fix Verification:
        Cannot create a booking pairing Customer A with a vehicle owned by Customer B.
        """
        other_customer = Customer.objects.create(
            name="Other Customer",
            phone="+91 9999888877",
            email="other@example.com"
        )
        payload = {
            "customer": other_customer.id,
            "vehicle": self.vehicle_1.id,  # belongs to self.customer, not other_customer
            "service_category": self.service.id,
        }
        res = self.client.post('/api/v1/bookings/', payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn("vehicle", str(res.data))

    def test_demo_simulator_advances_with_atomic_lock(self):
        """
        P0-2 Fix Verification:
        Demo simulator acquires lock using select_for_update(skip_locked=True)
        and calls service methods without duplicate re-locking errors.
        """
        b = Booking.objects.create(
            booking_number="BK-SIM-LOCK-001",
            customer=self.customer,
            vehicle=self.vehicle_1,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("1800.00"),
            is_demo_scenario=False
        )

        res = self.client.post('/api/v1/demo/simulate/')
        self.assertEqual(res.status_code, 200)

        b.refresh_from_db()
        self.assertEqual(b.status, Booking.STATUS_ASSIGNED)
        self.assertIsNotNone(b.mechanic)

    def test_attention_eta_formatted_in_ist(self):
        """
        P2-2 Fix Verification:
        Overdue arrival attention item must format the ETA in local Asia/Kolkata (IST),
        not in raw UTC.
        """
        now = timezone.now()
        # ETA set to 15:30 UTC = 21:00 IST
        eta = now - timedelta(minutes=20)
        Booking.objects.create(
            booking_number="BK-ETA-IST-001",
            customer=self.customer,
            vehicle=self.vehicle_1,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_ON_THE_WAY,
            amount=Decimal("1800.00"),
            started_at=now - timedelta(minutes=50),
            estimated_arrival_at=eta,
            arrived_at=None
        )

        attention = DashboardService.get_attention_items()
        overdue_items = [item for item in attention['items'] if item['booking_number'] == "BK-ETA-IST-001"]
        self.assertTrue(len(overdue_items) > 0)

        item = overdue_items[0]
        expected_ist_time = timezone.localtime(eta).strftime('%H:%M')
        self.assertIn(
            f"{expected_ist_time} IST",
            item['details'],
            f"Details should contain local time {expected_ist_time} IST, but got: {item['details']}"
        )

    def test_analytics_query_window_exact_buckets(self):
        """
        P2-1 Fix Verification:
        In 7d analytics, start_time must query exactly the 7 calendar days
        (local_today - 6 days through local_today).
        """
        res = DashboardService.get_analytics_bookings(range_param="7d")
        self.assertEqual(len(res['data']), 7)

        rev = DashboardService.get_analytics_revenue(range_param="7d")
        self.assertEqual(len(rev['data']), 7)

    def test_seed_data_idempotent_with_existing_categories(self):
        """
        P3 Fix Verification:
        seed_data does not raise IntegrityError when ServiceCategory already exists.
        """
        # Run seed command without --reset; must skip safely and not crash
        call_command('seed_data')
        self.assertTrue(ServiceCategory.objects.filter(id=self.service.id).exists())
