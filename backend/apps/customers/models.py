from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, db_index=True)
    email = models.EmailField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('SEDAN', 'Sedan'),
        ('SUV', 'SUV'),
        ('HATCHBACK', 'Hatchback'),
        ('TRUCK', 'Truck'),
        ('MOTORCYCLE', 'Motorcycle'),
        ('VAN', 'Van'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPE_CHOICES, default='SEDAN')

    def __str__(self):
        return f"{self.make} {self.model} ({self.registration_number})"
