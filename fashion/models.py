from django.db import models
from django.contrib.auth.models import User


class FashionSuggestion(models.Model):
    EVENT_CHOICES = [
        ('casual',   'Casual'),
        ('formal',   'Formal'),
        ('wedding',  'Wedding'),
        ('party',    'Party'),
        ('business', 'Business'),
        ('outdoor',  'Outdoor'),
        ('sports',   'Sports'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fashion_suggestions')
    image       = models.ImageField(upload_to='fashion/')
    event_type  = models.CharField(max_length=20, choices=EVENT_CHOICES)
    body_type   = models.CharField(max_length=30, blank=True)
    skin_tone   = models.CharField(max_length=30, blank=True)
    suggestions = models.JSONField(default=dict)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.event_type} ({self.created_at.date()})"
