from django.db import models


class Provider(models.Model):
    PROVIDER_TYPES = [
        ('dermatologist', 'Dermatologist'),
        ('salon',         'Salon'),
        ('clinic',        'Clinic'),
    ]

    name          = models.CharField(max_length=200)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    address       = models.TextField()
    city          = models.CharField(max_length=100)
    phone         = models.CharField(max_length=30, blank=True)
    email         = models.EmailField(blank=True)
    website       = models.URLField(blank=True)
    latitude      = models.FloatField(null=True, blank=True)
    longitude     = models.FloatField(null=True, blank=True)
    opening_time  = models.TimeField(null=True, blank=True)
    closing_time  = models.TimeField(null=True, blank=True)
    working_days  = models.CharField(
        max_length=100, default='Mon-Sat',
        help_text='e.g. Mon-Fri or Mon,Wed,Fri'
    )
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.provider_type})"
