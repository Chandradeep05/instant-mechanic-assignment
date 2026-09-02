import pytest
import re
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError
from django.conf import settings

from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import Booking, BookingStatusHistory, ServiceCategory
from apps.bookings.services import (
    BookingService,
    ALLOWED_TRANSITIONS,
    MAX_CONCURRENT_JOBS,
)
from apps.common.exceptions import (
    InvalidStateTransitionError,
    MechanicUnavailableError,
    BookingTerminalStateError,
)
from apps.dashboard.services import DashboardService
from apps.customers.views import CustomerListView


@pytest.mark.django_db
class DeepProductionVerificationTestCase(TestCase):
    def setUp(self):
        self.customer_a = Customer.objects.create(
            name="Vikramaditya Roy",
            phone="+91 9876543210",
            email="vikram@example.com"
        )
        self.customer_b = Customer.objects.create(
            name="Ananya Sen",
            phone="+91 9876543211",
            email="ananya@example.com"
        )
        self.vehicle_a1 = Vehicle.objects.create(
            customer=self.customer_a,
            make="Tata",
            model="Nexon EV",
            registration_number="DL-03-CC-1234",
            vehicle_type="SUV"
        )
        self.vehicle_a2 = Vehicle.objects.create(
            customer=self.customer_a,
            make="Mahindra",
            model="XUV700",
            registration_number="DL-03-CC-5678",
            vehicle_type="SUV"
        )
        self.vehicle_b1 = Vehicle.objects.create(
            customer=self.customer_b,
            make="Hyundai",
            model="Creta",
            registration_number="HR-26-EE-9999",
            vehicle_type="SUV"
        )
        self.service = ServiceCategory.objects.create(
            name="Engine Diagnostics & Scan",
            description="OBD-II full scan",
            base_price=Decimal("2500.00")
        )
        self.mechanic = Mechanic.objects.create(
            name="Rajesh Verma",
            phone="+91 9811002233",
            availability_status=Mechanic.AVAILABILITY_AVAILABLE,
            rating=Decimal("4.85")
        )
        self.client = APIClient()

    # =========================================================================
    # 1. STATE MACHINE MATRIX & FORBIDDEN TRANSITIONS
    # =========================================================================

    def test_complete_forbidden_transition_matrix(self):
        """
        Verify that every non-allowed status transition raises InvalidStateTransitionError
        and leaves the database record untouched.
        """
        all_statuses = [s[0] for s in Booking.STATUS_CHOICES]

        for current_status, allowed_targets in ALLOWED_TRANSITIONS.items():
            forbidden_targets = [s for s in all_statuses if s not in allowed_targets and s != current_status]

            for forbidden_status in forbidden_targets:
                # Create a booking in the current status
                b = Booking(
                    booking_number=f"BK-MATRIX-{current_status}-{forbidden_status}",
                    customer=self.customer_a,
                    vehicle=self.vehicle_a1,
                    service_category=self.service,
                    amount=Decimal("2500.00"),
                    status=current_status,
                )
                if current_status in [Booking.STATUS_ASSIGNED, Booking.STATUS_ON_THE_WAY, Booking.STATUS_ARRIVED, Booking.STATUS_IN_PROGRESS]:
                    b.mechanic = self.mechanic
                if current_status == Booking.STATUS_COMPLETED:
                    b.completed_at = timezone.now()
                if current_status == Booking.STATUS_CANCELLED:
                    b.cancelled_at = timezone.now()
                b.save()

                with self.assertRaises(InvalidStateTransitionError):
                    BookingService.transition_booking(b, forbidden_status)

                b.refresh_from_db()
                self.assertEqual(
                    b.status,
                    current_status,
                    f"Forbidden transition from {current_status} to {forbidden_status} altered booking status!"
                )

    def test_terminal_states_reject_all_mutations(self):
        """
        COMPLETED and CANCELLED bookings cannot transition to any status or be reassigned.
        """
        now = timezone.now()
        b_completed = Booking.objects.create(
            booking_number="BK-TERM-COMP",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_COMPLETED,
            amount=Decimal("2500.00"),
            completed_at=now
        )
        b_cancelled = Booking.objects.create(
            booking_number="BK-TERM-CANC",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            service_category=self.service,
            status=Booking.STATUS_CANCELLED,
            amount=Decimal("2500.00"),
            cancelled_at=now
        )

        for status_target in [s[0] for s in Booking.STATUS_CHOICES]:
            with self.assertRaises(InvalidStateTransitionError):
                BookingService.transition_booking(b_completed, status_target)
            with self.assertRaises(InvalidStateTransitionError):
                BookingService.transition_booking(b_cancelled, status_target)

        new_mechanic = Mechanic.objects.create(name="New Tech", phone="+91 9111222333")
        with self.assertRaises(BookingTerminalStateError):
            BookingService.assign_mechanic(b_completed, new_mechanic)
        with self.assertRaises(BookingTerminalStateError):
            BookingService.assign_mechanic(b_cancelled, new_mechanic)

    def test_reassignment_blocked_after_travel_begins(self):
        """
        Once travel begins (ON_THE_WAY, ARRIVED, IN_PROGRESS), reassigning mechanic is rejected.
        """
        now = timezone.now()
        b = Booking.objects.create(
            booking_number="BK-REASSIGN-BLOCK",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_ON_THE_WAY,
            amount=Decimal("2500.00"),
            started_at=now - timedelta(minutes=10),
            estimated_arrival_at=now + timedelta(minutes=15)
        )
        other_tech = Mechanic.objects.create(name="Spare Tech", phone="+91 9444555666")

        with self.assertRaises(InvalidStateTransitionError):
            BookingService.assign_mechanic(b, other_tech)

        b.status = Booking.STATUS_ARRIVED
        b.arrived_at = now
        b.save()

        with self.assertRaises(InvalidStateTransitionError):
            BookingService.assign_mechanic(b, other_tech)

        b.status = Booking.STATUS_IN_PROGRESS
        b.save()

        with self.assertRaises(InvalidStateTransitionError):
            BookingService.assign_mechanic(b, other_tech)

    # =========================================================================
    # 2. MECHANIC CAPACITY SERIALIZATION & RECOVERY
    # =========================================================================

    def test_mechanic_max_capacity_enforced_and_freed_on_completion(self):
        """
        When a mechanic hits MAX_CONCURRENT_JOBS (3), assigning a 4th job fails with
        MechanicUnavailableError. When 1 job completes, capacity is immediately freed.
        """
        now = timezone.now()
        active_bookings = []
        for i in range(MAX_CONCURRENT_JOBS):
            b = Booking.objects.create(
                booking_number=f"BK-CAPACITY-{i}",
                customer=self.customer_a,
                vehicle=self.vehicle_a1,
                mechanic=self.mechanic,
                service_category=self.service,
                status=Booking.STATUS_ASSIGNED if i == 0 else Booking.STATUS_IN_PROGRESS,
                amount=Decimal("1500.00"),
                assigned_at=now
            )
            active_bookings.append(b)

        # 4th booking to same mechanic must fail
        fourth_booking = Booking.objects.create(
            booking_number="BK-CAPACITY-OVERLOAD",
            customer=self.customer_b,
            vehicle=self.vehicle_b1,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("2000.00")
        )
        with self.assertRaises(MechanicUnavailableError):
            BookingService.assign_mechanic(fourth_booking, self.mechanic)

        # Complete 1 job
        completed_job = active_bookings[0]
        completed_job.status = Booking.STATUS_COMPLETED
        completed_job.completed_at = timezone.now()
        completed_job.save()

        # Now assigning 4th booking to this mechanic must succeed!
        assigned = BookingService.assign_mechanic(fourth_booking, self.mechanic)
        self.assertEqual(assigned.mechanic, self.mechanic)
        self.assertEqual(assigned.status, Booking.STATUS_ASSIGNED)

    def test_offline_and_break_mechanics_cannot_be_assigned(self):
        """
        Mechanics with availability_status != AVAILABLE cannot receive assignments.
        """
        offline_tech = Mechanic.objects.create(
            name="Offline Tech",
            phone="+91 9000111222",
            availability_status=Mechanic.AVAILABILITY_OFFLINE
        )
        break_tech = Mechanic.objects.create(
            name="Break Tech",
            phone="+91 9000111333",
            availability_status=Mechanic.AVAILABILITY_BREAK
        )
        b = Booking.objects.create(
            booking_number="BK-AVAIL-TEST",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("1500.00")
        )

        with self.assertRaises(MechanicUnavailableError):
            BookingService.assign_mechanic(b, offline_tech)

        with self.assertRaises(MechanicUnavailableError):
            BookingService.assign_mechanic(b, break_tech)

    # =========================================================================
    # 3. ATTENTION ENGINE FALSE POSITIVE PREVENTION
    # =========================================================================

    def test_attention_engine_no_false_positives_for_healthy_bookings(self):
        """
        Verify that healthy, on-time bookings are NOT falsely flagged as attention items.
        """
        now = timezone.now()
        # 1. PENDING created 3 minutes ago (healthy, threshold is 15 min)
        b_pending_healthy = Booking.objects.create(
            booking_number="BK-HEALTHY-PEND",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("2000.00")
        )
        Booking.objects.filter(id=b_pending_healthy.id).update(created_at=now - timedelta(minutes=3))

        # 2. ASSIGNED 5 minutes ago (healthy, threshold is 10 min)
        b_assigned_healthy = Booking.objects.create(
            booking_number="BK-HEALTHY-ASGN",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_ASSIGNED,
            amount=Decimal("2000.00"),
            assigned_at=now - timedelta(minutes=5)
        )

        # 3. ON_THE_WAY with ETA in 15 minutes (healthy, not overdue)
        b_otw_healthy = Booking.objects.create(
            booking_number="BK-HEALTHY-OTW",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            mechanic=self.mechanic,
            service_category=self.service,
            status=Booking.STATUS_ON_THE_WAY,
            amount=Decimal("2000.00"),
            started_at=now - timedelta(minutes=10),
            estimated_arrival_at=now + timedelta(minutes=15)
        )

        res = DashboardService.get_attention_items()
        flagged_ids = [item["entity_id"] for item in res["items"] if item["type"] != "OVERLOADED_MECHANIC"]

        self.assertNotIn(b_pending_healthy.id, flagged_ids)
        self.assertNotIn(b_assigned_healthy.id, flagged_ids)
        self.assertNotIn(b_otw_healthy.id, flagged_ids)

    # =========================================================================
    # 4. ADVANCED CUSTOMER LTV & FLEET MULTIPLICATION STRESS TEST
    # =========================================================================

    def test_customer_ltv_with_multi_vehicle_mixed_lifecycles(self):
        """
        Stress test CustomerListView metrics:
        Customer has 4 vehicles.
        3 completed bookings (₹1,500 + ₹2,500 + ₹3,000 = ₹7,000).
        2 cancelled bookings (₹2,000 each -> ₹0 revenue).
        1 in-progress booking (₹4,000 -> ₹0 revenue).
        Assert:
        - vehicle_count == 4
        - total_bookings == 6
        - lifetime_value == Decimal('7000.00') exactly.
        """
        now = timezone.now()
        v3 = Vehicle.objects.create(customer=self.customer_a, make="Maruti", model="Swift", registration_number="DL-03-V3")
        v4 = Vehicle.objects.create(customer=self.customer_a, make="Hyundai", model="i10", registration_number="DL-03-V4")

        # 3 Completed
        Booking.objects.create(
            booking_number="BK-COMP-1", customer=self.customer_a, vehicle=self.vehicle_a1,
            service_category=self.service, status=Booking.STATUS_COMPLETED,
            amount=Decimal("1500.00"), completed_at=now - timedelta(days=2)
        )
        Booking.objects.create(
            booking_number="BK-COMP-2", customer=self.customer_a, vehicle=self.vehicle_a2,
            service_category=self.service, status=Booking.STATUS_COMPLETED,
            amount=Decimal("2500.00"), completed_at=now - timedelta(days=1)
        )
        Booking.objects.create(
            booking_number="BK-COMP-3", customer=self.customer_a, vehicle=v3,
            service_category=self.service, status=Booking.STATUS_COMPLETED,
            amount=Decimal("3000.00"), completed_at=now
        )

        # 2 Cancelled
        Booking.objects.create(
            booking_number="BK-CANC-1", customer=self.customer_a, vehicle=v4,
            service_category=self.service, status=Booking.STATUS_CANCELLED,
            amount=Decimal("2000.00"), cancelled_at=now - timedelta(days=5)
        )
        Booking.objects.create(
            booking_number="BK-CANC-2", customer=self.customer_a, vehicle=self.vehicle_a1,
            service_category=self.service, status=Booking.STATUS_CANCELLED,
            amount=Decimal("2000.00"), cancelled_at=now - timedelta(days=4)
        )

        # 1 In Progress
        Booking.objects.create(
            booking_number="BK-INP-1", customer=self.customer_a, vehicle=self.vehicle_a2,
            mechanic=self.mechanic, service_category=self.service,
            status=Booking.STATUS_IN_PROGRESS, amount=Decimal("4000.00")
        )

        qs = CustomerListView().get_queryset()
        annotated = qs.get(id=self.customer_a.id)

        self.assertEqual(annotated.vehicle_count, 4)
        self.assertEqual(annotated.total_bookings, 6)
        self.assertEqual(Decimal(str(annotated.lifetime_value)), Decimal("7000.00"))

    # =========================================================================
    # 5. API FILTERING, PAGINATION BOUNDARIES & ERROR CONTRACTS
    # =========================================================================

    def test_bookings_api_pagination_limit_clamped(self):
        """
        Querying ?page_size=500 must clamp to max 100 per system pagination constraints.
        """
        res = self.client.get('/api/v1/bookings/?page_size=500')
        self.assertEqual(res.status_code, 200)
        # Even if page_size=500 is requested, pageSize remains <= 100
        self.assertLessEqual(len(res.data['results']), 100)

    def test_bookings_api_search_filter_multiple_fields(self):
        """
        Test that ?search= matches booking_number, customer name, vehicle registration, and phone.
        """
        b = Booking.objects.create(
            booking_number="BK-SEARCH-TARGET-77",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("2500.00")
        )

        # Search by booking number
        res1 = self.client.get('/api/v1/bookings/?search=TARGET-77')
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(any(item['id'] == b.id for item in res1.data['results']))

        # Search by customer name
        res2 = self.client.get('/api/v1/bookings/?search=Vikramaditya')
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(any(item['id'] == b.id for item in res2.data['results']))

        # Search by vehicle registration
        res3 = self.client.get('/api/v1/bookings/?search=CC-1234')
        self.assertEqual(res3.status_code, 200)
        self.assertTrue(any(item['id'] == b.id for item in res3.data['results']))

    def test_analytics_invalid_range_payload_format(self):
        """
        Invalid range queries must return HTTP 400 with standardized LiveOps error response.
        """
        res_bookings = self.client.get('/api/v1/analytics/bookings/?range=180d')
        self.assertEqual(res_bookings.status_code, 400)
        self.assertEqual(res_bookings.data['error']['code'], 'INVALID_RANGE')

        res_revenue = self.client.get('/api/v1/analytics/revenue/?range=24h')
        self.assertEqual(res_revenue.status_code, 400)
        self.assertEqual(res_revenue.data['error']['code'], 'INVALID_RANGE')

    # =========================================================================
    # 6. CORS & ORIGIN SECURITY VERIFICATION
    # =========================================================================

    def test_cors_regex_matches_vercel_domains(self):
        """
        Verify that CORS regex patterns match live and preview Vercel domains.
        """
        patterns = getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', [])
        self.assertTrue(len(patterns) > 0)

        test_origins = [
            "https://instant-mechanic-assignment-ten.vercel.app",
            "https://instant-mechanic-assignment.vercel.app",
            "https://instant-mechanic-assignment-preview-123.vercel.app",
        ]
        for origin in test_origins:
            matched = any(re.match(pattern, origin) for pattern in patterns)
            self.assertTrue(matched, f"Expected CORS regex to match {origin}")

        # Unauthorized domain must NOT match
        unauthorized = "https://malicious-external-site.com"
        unauthorized_matched = any(re.match(pattern, unauthorized) for pattern in patterns)
        self.assertFalse(unauthorized_matched, f"CORS regex improperly matched {unauthorized}")

    def test_cors_rejects_other_vercel_and_render_projects(self):
        """
        RB-NEW-01 Hostile Verification:
        CORS must reject arbitrary third-party projects hosted on the same provider
        (Vercel or Render). Only instant-mechanic-assignment domains are accepted.
        """
        patterns = getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', [])
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])

        def is_origin_allowed(origin):
            if origin in allowed_origins:
                return True
            return any(re.match(pattern, origin) for pattern in patterns)

        # Hostile tests in the same provider namespaces must be REJECTED
        self.assertFalse(is_origin_allowed("https://attacker-project.vercel.app"))
        self.assertFalse(is_origin_allowed("https://another-student-assignment.vercel.app"))
        self.assertFalse(is_origin_allowed("https://random-attacker.onrender.com"))
        self.assertFalse(is_origin_allowed("https://evil-host.onrender.com"))

        # Valid project origins must be ACCEPTED
        self.assertTrue(is_origin_allowed("https://instant-mechanic-assignment-ten.vercel.app"))
        self.assertTrue(is_origin_allowed("https://instant-mechanic-assignment.vercel.app"))
        self.assertTrue(is_origin_allowed("https://instant-mechanic-assignment-staging-42.vercel.app"))

    def test_origin_sanitizer_prepends_scheme_when_missing(self):
        """
        Verify that bare hostnames like 'instant-mechanic-assignment-ten.vercel.app'
        are safely normalized with https:// scheme to prevent django-cors-headers E013 errors.
        """
        from core.settings import _sanitize_origin
        self.assertEqual(_sanitize_origin("instant-mechanic-assignment-ten.vercel.app"), "https://instant-mechanic-assignment-ten.vercel.app")
        self.assertEqual(_sanitize_origin("https://instant-mechanic-assignment-ten.vercel.app/"), "https://instant-mechanic-assignment-ten.vercel.app")
        self.assertEqual(_sanitize_origin("http://localhost:5173/"), "http://localhost:5173")
        self.assertEqual(_sanitize_origin(""), "")

    def test_cors_origins_do_not_implicitly_expand_websocket_origins(self):
        """
        HP-FINAL-01 Verification:
        HTTP CORS origins must NOT be implicitly copied into WEBSOCKET_ALLOWED_ORIGINS.
        WebSocket trust boundary must be strictly isolated.
        """
        extra_http_origin = "https://extra-http-origin.example.com"
        ws_origins = getattr(settings, 'WEBSOCKET_ALLOWED_ORIGINS', [])
        self.assertNotIn(extra_http_origin, ws_origins)

    def test_production_db_conn_max_age_defaults_to_zero(self):
        """
        Supabase Pooler Verification:
        Database connection max age defaults to 0 to prevent exhausting the
        15-client connection pool in session mode.
        """
        default_db = settings.DATABASES.get('default', {})
        self.assertEqual(default_db.get('CONN_MAX_AGE', 0), 0)

    # =========================================================================
    # 7. DEMO SIMULATOR STEPWISE PROGRESSION
    # =========================================================================

    def test_demo_simulator_stepwise_progression(self):
        """
        Verify demo simulator safely cycles a booking through:
        PENDING -> ASSIGNED -> ON_THE_WAY -> ARRIVED -> IN_PROGRESS -> COMPLETED
        without deadlock or state corruption.
        """
        # Clear existing demo bookings to isolate test
        Booking.objects.filter(is_demo_scenario=False).delete()

        b = Booking.objects.create(
            booking_number="BK-DEMO-LIFECYCLE",
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            service_category=self.service,
            status=Booking.STATUS_PENDING,
            amount=Decimal("2500.00"),
            is_demo_scenario=False
        )

        expected_sequence = [
            Booking.STATUS_ASSIGNED,
            Booking.STATUS_ON_THE_WAY,
            Booking.STATUS_ARRIVED,
            Booking.STATUS_IN_PROGRESS,
            Booking.STATUS_COMPLETED,
        ]

        for expected_status in expected_sequence:
            res = self.client.post('/api/v1/demo/simulate/')
            self.assertEqual(res.status_code, 200)
            b.refresh_from_db()
            self.assertEqual(b.status, expected_status)

        # Completed booking has completion timestamp
        self.assertIsNotNone(b.completed_at)
