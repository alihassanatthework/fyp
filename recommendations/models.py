from django.db import models
from django.contrib.auth.models import User
from image_analysis.models import AnalysisResult


class Recommendation(models.Model):
    """
    Individual treatment recommendation linked to one analysis result.
    The AI pipeline currently returns recommendations as a JSON blob;
    this model stores each recommendation as a proper row for easier
    querying, filtering, and future export (PDF, email, etc.).
    """
    CATEGORY_CHOICES = [
        ('morning_routine', 'Morning Routine'),
        ('evening_routine', 'Evening Routine'),
        ('weekly_routine',  'Weekly Routine'),
        ('product',         'Product'),
        ('safety_note',     'Safety Note'),
        ('dermatologist',   'Dermatologist'),
        ('general',         'General'),
    ]

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='recommendation_items')

    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='general')
    title       = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField()
    order       = models.PositiveIntegerField(default=0)  # display order

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.category}: {self.description[:60]}"
