from django.db import models

class Mechanic(models.Model):
    AVAILABILITY_AVAILABLE = 'AVAILABLE'
    AVAILABILITY_OFFLINE = 'OFFLINE'
    AVAILABILITY_BREAK = 'BREAK'

    AVAILABILITY_CHOICES = [
        (AVAILABILITY_AVAILABLE, 'Available'),
        (AVAILABILITY_OFFLINE, 'Offline'),
        (AVAILABILITY_BREAK, 'On Break'),
    ]

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    availability_status = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_AVAILABLE,
        db_index=True
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=0) & models.Q(rating__lte=5),
                name='mechanic_rating_between_0_and_5',
            ),
        ]

    def __str__(self):
        return f"{self.name} [{self.availability_status}]"
