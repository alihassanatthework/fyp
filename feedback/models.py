from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from image_analysis.models import AnalysisResult


class AnalysisFeedback(models.Model):
    """
    User feedback on a single AI analysis result.
    Allows users to rate accuracy and leave an optional comment.
    This data can be used later to improve AI model accuracy.
    """
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    analysis = models.OneToOneField(AnalysisResult, on_delete=models.CASCADE, related_name='feedback')
    rating   = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 = very inaccurate, 5 = very accurate"
    )
    comment    = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} → {self.analysis.analysis_id} ({self.rating}★)"
