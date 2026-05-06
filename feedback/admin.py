from django.contrib import admin
from .models import AnalysisFeedback

@admin.register(AnalysisFeedback)
class AnalysisFeedbackAdmin(admin.ModelAdmin):
    list_display  = ("user", "analysis", "rating", "created_at")
    list_filter   = ("rating",)
    search_fields = ("user__email", "analysis__analysis_id", "comment")
    ordering      = ("-created_at",)
