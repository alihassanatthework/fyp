from django.db import models
from django.contrib.auth.models import User


class MakeupSuggestion(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='makeup_suggestions')
    image       = models.ImageField(upload_to='makeup/')
    face_shape  = models.CharField(max_length=30, blank=True)
    skin_tone   = models.CharField(max_length=30, blank=True)
    suggestions = models.JSONField(default=dict)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.face_shape} ({self.created_at.date()})"
