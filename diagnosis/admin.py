from django.contrib import admin
from .models import DiagnosisReport


@admin.register(DiagnosisReport)
class DiagnosisReportAdmin(admin.ModelAdmin):
    list_display  = ('user', 'primary_condition', 'severity_level', 'confidence_score', 'recommend_dermatologist', 'created_at')
    list_filter   = ('severity_level', 'recommend_dermatologist')
    search_fields = ('user__email', 'primary_condition')
    ordering      = ('-created_at',)
    readonly_fields = ('user', 'analysis', 'created_at')
