from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, F, Q
from rest_framework.exceptions import ValidationError
from apps.bookings.models import Booking, ServiceCategory
from apps.mechanics.models import Mechanic
from apps.customers.models import Customer

VALID_ANALYTICS_RANGES = {"24h", "7d", "30d"}
VALID_REVENUE_RANGES = {"7d", "30d"}

class DashboardService:
    @staticmethod
    def get_attention_items():
        """
        Calculates non-overlapping attention alerts based on deterministic rules:
        - CRITICAL: PENDING booking unassigned > 15m
        - HIGH: ASSIGNED booking stuck > 10m without moving to ON_THE_WAY
        - WARNING (Delayed): ON_THE_WAY booking with passed ETA and arrived_at is NULL
        - WARNING (Overloaded): Mechanic with >= 4 active bookings
        """
        now = timezone.now()
        items = []

        # 1. CRITICAL: PENDING > 15 min
        critical_cutoff = now - timedelta(minutes=15)
        critical_bookings = Booking.objects.filter(
            status=Booking.STATUS_PENDING,
            created_at__lte=critical_cutoff
        ).select_related('customer', 'service_category')

        for b in critical_bookings:
            age_minutes = max(15, int((now - b.created_at).total_seconds() / 60))
            items.append({
                "id": f"crit-booking-{b.id}",
                "type": "UNASSIGNED_BOOKING",
                "severity": "CRITICAL",
                "severity_rank": 1,
                "entity_type": "booking",
                "entity_id": b.id,
                "booking_number": b.booking_number,
                "title": f"Unassigned for {age_minutes} minutes",
                "details": f"Customer {b.customer.name} waiting for {b.service_category.name} assignment.",
                "created_at": b.created_at.isoformat(),
                "action_type": "ASSIGN_MECHANIC",
            })

        # 2. HIGH: ASSIGNED > 10 min without moving to ON_THE_WAY
        high_cutoff = now - timedelta(minutes=10)
        high_bookings = Booking.objects.filter(
            status=Booking.STATUS_ASSIGNED,
            assigned_at__lte=high_cutoff
        ).select_related('customer', 'mechanic', 'service_category')

        for b in high_bookings:
            assigned_age = int((now - b.assigned_at).total_seconds() / 60) if b.assigned_at else 10
            items.append({
                "id": f"high-booking-{b.id}",
                "type": "DELAYED_DISPATCH",
                "severity": "HIGH",
                "severity_rank": 2,
                "entity_type": "booking",
                "entity_id": b.id,
                "booking_number": b.booking_number,
                "title": f"Dispatch delayed ({assigned_age} min)",
                "details": f"Mechanic {b.mechanic.name if b.mechanic else 'Assigned'} has not started travel after {assigned_age} minutes.",
                "created_at": (b.assigned_at or b.created_at).isoformat(),
                "action_type": "VIEW_BOOKING",
            })

        # 3. WARNING: ON_THE_WAY and ETA passed, arrived_at is NULL
        delayed_bookings = Booking.objects.filter(
            status=Booking.STATUS_ON_THE_WAY,
            estimated_arrival_at__lt=now,
            arrived_at__isnull=True
        ).select_related('customer', 'mechanic', 'service_category')

        for b in delayed_bookings:
            overdue_mins = max(1, int((now - b.estimated_arrival_at).total_seconds() / 60)) if b.estimated_arrival_at else 5
            items.append({
                "id": f"warn-delay-{b.id}",
                "type": "OVERDUE_ARRIVAL",
                "severity": "WARNING",
                "severity_rank": 3,
                "entity_type": "booking",
                "entity_id": b.id,
                "booking_number": b.booking_number,
                "title": f"Delayed arrival: ETA exceeded by {overdue_mins}m",
                "details": f"Mechanic {b.mechanic.name if b.mechanic else 'Unknown'} was expected at {b.estimated_arrival_at.strftime('%H:%M')} IST.",
                "created_at": (b.started_at or b.created_at).isoformat(),
                "action_type": "VIEW_BOOKING",
            })

        # 4. WARNING: Overloaded mechanics (>= 4 active jobs)
        active_statuses = [
            Booking.STATUS_ASSIGNED,
            Booking.STATUS_ON_THE_WAY,
            Booking.STATUS_ARRIVED,
            Booking.STATUS_IN_PROGRESS
        ]
        overloaded_mechanics = Mechanic.objects.annotate(
            active_jobs=Count('bookings', filter=Q(bookings__status__in=active_statuses))
        ).filter(active_jobs__gte=4)

        for m in overloaded_mechanics:
            items.append({
                "id": f"warn-overload-{m.id}",
                "type": "OVERLOADED_MECHANIC",
                "severity": "WARNING",
                "severity_rank": 3,
                "entity_type": "mechanic",
                "entity_id": m.id,
                "booking_number": None,
                "title": f"Mechanic overloaded: {m.name} ({m.active_jobs} active jobs)",
                "details": f"Mechanic {m.name} currently has {m.active_jobs} concurrent assignments.",
                "created_at": now.isoformat(),
                "action_type": "VIEW_MECHANIC",
            })

        # Sort: severity_rank ASC (CRITICAL=1, HIGH=2, WARNING=3), created_at ASC (oldest first)
        items.sort(key=lambda x: (x["severity_rank"], x["created_at"]))
        return {"items": items, "count": len(items)}

    @staticmethod
    def get_overview_kpis():
        """
        Calculates Overview KPIs and server-side deltas.
        All time calculations use IST (Asia/Kolkata) via Django's USE_TZ=True + TIME_ZONE setting.
        """
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_yesterday = start_of_today - timedelta(days=1)

        # Bookings counts
        total_bookings = Booking.objects.count()
        today_bookings = Booking.objects.filter(created_at__gte=start_of_today).count()
        yesterday_bookings = Booking.objects.filter(
            created_at__gte=start_of_yesterday,
            created_at__lt=start_of_today
        ).count()

        today_bookings_delta = (
            round(((today_bookings - yesterday_bookings) / yesterday_bookings) * 100, 1)
            if yesterday_bookings > 0 else 0.0
        )

        completed_bookings = Booking.objects.filter(status=Booking.STATUS_COMPLETED).count()
        pending_bookings = Booking.objects.filter(status=Booking.STATUS_PENDING).count()
        cancelled_bookings = Booking.objects.filter(status=Booking.STATUS_CANCELLED).count()

        # Revenue
        total_revenue_aggr = Booking.objects.filter(
            status=Booking.STATUS_COMPLETED
        ).aggregate(sum=Sum('amount'))['sum'] or 0.00

        today_revenue_aggr = Booking.objects.filter(
            status=Booking.STATUS_COMPLETED,
            completed_at__gte=start_of_today
        ).aggregate(sum=Sum('amount'))['sum'] or 0.00

        yesterday_revenue_aggr = Booking.objects.filter(
            status=Booking.STATUS_COMPLETED,
            completed_at__gte=start_of_yesterday,
            completed_at__lt=start_of_today
        ).aggregate(sum=Sum('amount'))['sum'] or 0.00

        today_revenue_delta = (
            round(((float(today_revenue_aggr) - float(yesterday_revenue_aggr)) / float(yesterday_revenue_aggr)) * 100, 1)
            if float(yesterday_revenue_aggr) > 0 else 0.0
        )

        # Mechanics
        # "active" = not OFFLINE (includes AVAILABLE + BREAK)
        # "available" = AVAILABLE + zero active jobs (truly dispatchable)
        # "busy" = explicitly has >= 1 active job (not derived by subtraction)
        active_statuses = [
            Booking.STATUS_ASSIGNED,
            Booking.STATUS_ON_THE_WAY,
            Booking.STATUS_ARRIVED,
            Booking.STATUS_IN_PROGRESS
        ]
        active_mechanics_count = Mechanic.objects.exclude(
            availability_status=Mechanic.AVAILABILITY_OFFLINE
        ).count()

        available_mechanics_count = Mechanic.objects.filter(
            availability_status=Mechanic.AVAILABILITY_AVAILABLE
        ).annotate(
            active_count=Count('bookings', filter=Q(bookings__status__in=active_statuses))
        ).filter(active_count=0).count()

        # Explicitly count mechanics with >= 1 active job REGARDLESS of availability status.
        # A mechanic on BREAK or OFFLINE with an unfinished job is still operationally busy.
        busy_mechanics_count = Mechanic.objects.annotate(
            active_count=Count('bookings', filter=Q(bookings__status__in=active_statuses))
        ).filter(active_count__gt=0).count()

        # New Customers (today)
        new_customers_today = Customer.objects.filter(created_at__gte=start_of_today).count()
        new_customers_yesterday = Customer.objects.filter(
            created_at__gte=start_of_yesterday,
            created_at__lt=start_of_today
        ).count()
        new_customers_delta = new_customers_today - new_customers_yesterday

        # Average Response Time (assigned_at - created_at) — database aggregated over last 30 days
        # Returns null if no data exists; never fabricates a fallback value.
        thirty_days_ago = now - timedelta(days=30)
        valid_assignments = Booking.objects.filter(
            assigned_at__isnull=False,
            created_at__isnull=False,
            assigned_at__gte=F('created_at'),      # sanity: assigned must be after created
            assigned_at__lte=F('created_at') + timedelta(hours=3),  # cap at 3h (reasonable upper bound)
            created_at__gte=thirty_days_ago
        ).values_list('created_at', 'assigned_at')

        durations = [(a - c).total_seconds() / 60.0 for c, a in valid_assignments]
        avg_response_minutes = round(sum(durations) / len(durations), 1) if durations else None

        return {
            "total_bookings": total_bookings,
            "today_bookings": today_bookings,
            "today_bookings_delta_pct": today_bookings_delta,
            "completed_bookings": completed_bookings,
            "pending_bookings": pending_bookings,
            "cancelled_bookings": cancelled_bookings,
            "total_revenue": float(total_revenue_aggr),
            "today_revenue": float(today_revenue_aggr),
            "today_revenue_delta_pct": today_revenue_delta,
            "active_mechanics": active_mechanics_count,
            "available_mechanics": available_mechanics_count,
            "busy_mechanics": busy_mechanics_count,
            "new_customers": new_customers_today,
            "new_customers_delta": new_customers_delta,
            "avg_response_time_minutes": avg_response_minutes,  # null when no data — never fabricated
        }

    @staticmethod
    def get_analytics_bookings(range_param="7d"):
        """
        Single-pass server-side aggregation for bookings volume timeline.
        """
        if range_param not in VALID_ANALYTICS_RANGES:
            raise ValidationError(
                f"Invalid range '{range_param}'. Must be one of: {sorted(VALID_ANALYTICS_RANGES)}"
            )

        now = timezone.now()

        if range_param == "24h":
            start_time = now - timedelta(hours=24)
            buckets = {}
            for i in range(23, -1, -1):
                h_time = now - timedelta(hours=i)
                label = h_time.strftime('%H:00')
                buckets[label] = {"timestamp": label, "bookings": 0, "completed": 0, "cancelled": 0}

            for created, status in Booking.objects.filter(created_at__gte=start_time).values_list('created_at', 'status'):
                label = created.strftime('%H:00')
                if label in buckets:
                    buckets[label]["bookings"] += 1
                    if status == Booking.STATUS_COMPLETED:
                        buckets[label]["completed"] += 1
                    elif status == Booking.STATUS_CANCELLED:
                        buckets[label]["cancelled"] += 1
        else:
            days = 30 if range_param == "30d" else 7
            start_time = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            buckets = {}
            for i in range(days - 1, -1, -1):
                d_time = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                label = d_time.strftime('%b %d')
                buckets[label] = {"timestamp": label, "bookings": 0, "completed": 0, "cancelled": 0}

            for created, status in Booking.objects.filter(created_at__gte=start_time).values_list('created_at', 'status'):
                label = created.strftime('%b %d')
                if label in buckets:
                    buckets[label]["bookings"] += 1
                    if status == Booking.STATUS_COMPLETED:
                        buckets[label]["completed"] += 1
                    elif status == Booking.STATUS_CANCELLED:
                        buckets[label]["cancelled"] += 1

        return {"range": range_param, "data": list(buckets.values())}

    @staticmethod
    def get_analytics_revenue(range_param="7d"):
        """
        Single-pass server-side aggregation for revenue timeline.
        """
        if range_param not in VALID_REVENUE_RANGES:
            raise ValidationError(
                f"Invalid range '{range_param}'. Must be one of: {sorted(VALID_REVENUE_RANGES)}"
            )

        now = timezone.now()
        days = 30 if range_param == "30d" else 7
        start_time = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

        buckets = {}
        for i in range(days - 1, -1, -1):
            d_time = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            label = d_time.strftime('%b %d')
            buckets[label] = {"timestamp": label, "revenue": 0.0}

        for completed, amount in Booking.objects.filter(
            status=Booking.STATUS_COMPLETED,
            completed_at__gte=start_time
        ).values_list('completed_at', 'amount'):
            if completed:
                label = completed.strftime('%b %d')
                if label in buckets:
                    buckets[label]["revenue"] = round(buckets[label]["revenue"] + float(amount or 0.0), 2)

        return {"range": range_param, "data": list(buckets.values())}

    @staticmethod
    def get_analytics_status():
        total = Booking.objects.count()
        status_counts = Booking.objects.values('status').annotate(count=Count('id'))
        status_map = {item['status']: item['count'] for item in status_counts}
        all_statuses = [
            Booking.STATUS_PENDING,
            Booking.STATUS_ASSIGNED,
            Booking.STATUS_ON_THE_WAY,
            Booking.STATUS_ARRIVED,
            Booking.STATUS_IN_PROGRESS,
            Booking.STATUS_COMPLETED,
            Booking.STATUS_CANCELLED,
        ]

        data = []
        for s in all_statuses:
            c = status_map.get(s, 0)
            pct = round((c / total * 100), 1) if total > 0 else 0.0
            data.append({"status": s, "count": c, "percentage": pct})

        return {"total": total, "distribution": data}

    @staticmethod
    def get_analytics_services():
        services = ServiceCategory.objects.annotate(
            total_bookings=Count('bookings'),
            completed_bookings=Count('bookings', filter=Q(bookings__status=Booking.STATUS_COMPLETED)),
            total_revenue=Sum('bookings__amount', filter=Q(bookings__status=Booking.STATUS_COMPLETED))
        ).order_by('-total_bookings')

        return {
            "services": [
                {
                    "id": s.id,
                    "name": s.name,
                    "total_bookings": s.total_bookings,
                    "completed_bookings": s.completed_bookings,
                    "total_revenue": float(s.total_revenue or 0.00),
                }
                for s in services
            ]
        }
