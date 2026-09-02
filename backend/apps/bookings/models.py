from django.db import models
from django.db.models import Q
from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic


class ServiceCategory(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default='')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name_plural = 'Service categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (₹{self.base_price})"


class Booking(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_ON_THE_WAY = 'ON_THE_WAY'
    STATUS_ARRIVED = 'ARRIVED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ASSIGNED, 'Assigned'),
        (STATUS_ON_THE_WAY, 'On The Way'),
        (STATUS_ARRIVED, 'Arrived'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    booking_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bookings')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='bookings')
    mechanic = models.ForeignKey(Mechanic, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='bookings')

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Protect deliberate live attention scenario items from random simulation
    is_demo_scenario = models.BooleanField(default=False, db_index=True)

    # Lifecycle Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    estimated_arrival_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['mechanic', 'status']),
            models.Index(fields=['service_category']),
        ]
        constraints = [
            # Domain invariant: booking amount must never be negative
            models.CheckConstraint(
                check=Q(amount__gte=0),
                name='booking_amount_non_negative',
            ),
            # Domain invariant: active statuses require an assigned mechanic.
            # If status is ASSIGNED/ON_THE_WAY/ARRIVED/IN_PROGRESS, then mechanic_id must NOT be NULL.
            # This is the DB-level enforcement of the rule that assign_mechanic() is the only path
            # to ASSIGNED status — the generic transition endpoint cannot create orphaned assignments.
            models.CheckConstraint(
                check=(
                    ~Q(status__in=['ASSIGNED', 'ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS'])
                    | Q(mechanic__isnull=False)
                ),
                name='active_status_requires_mechanic',
            ),
        ]

    def __str__(self):
        return f"{self.booking_number} - {self.status} (₹{self.amount})"


class BookingStatusHistory(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.CharField(max_length=100, default='OPERATOR')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['changed_at']
        verbose_name_plural = 'Booking status histories'

    def __str__(self):
        return f"{self.booking.booking_number}: {self.previous_status} -> {self.new_status} at {self.changed_at}"
