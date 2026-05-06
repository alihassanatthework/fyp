from django.db import models
from django.contrib.auth.models import User
from image_analysis.models import AnalysisResult


class DiagnosisReport(models.Model):
    """
    Structured diagnosis report generated per analysis.
    Stores the top detected condition, confidence, and a short summary
    that can be displayed on the report page or exported as PDF later.
    """
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diagnoses')
    analysis  = models.OneToOneField(AnalysisResult, on_delete=models.CASCADE, related_name='diagnosis')

    # Top detected condition from the AI pipeline
    primary_condition    = models.CharField(max_length=100, blank=True, default='')
    confidence_score     = models.FloatField(default=0.0)   # 0.0 – 100.0
    severity_level       = models.CharField(max_length=20,  default='Mild')
    all_conditions       = models.JSONField(default=list)   # full conditions list

    # Dermatologist flag
    recommend_dermatologist = models.BooleanField(default=False)

    # Short auto-generated summary (can be populated by LLM or template)
    summary = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} | {self.primary_condition} | {self.severity_level}"
