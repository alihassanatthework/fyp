from django.db import models
from django.contrib.auth.models import User
from providers.models import Provider


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    provider   = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='bookings')
    date       = models.DateField()
    time       = models.TimeField()
    notes      = models.TextField(blank=True, help_text='Any specific concerns or notes')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.user.email} → {self.provider.name} on {self.date} at {self.time}"
