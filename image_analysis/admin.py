from django.contrib import admin
from .models import AnalysisResult


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display  = ('analysis_id', 'user', 'analysis_type', 'severity_label', 'max_severity', 'recommend_dermatologist', 'created_at')
    list_filter   = ('analysis_type', 'severity_label', 'recommend_dermatologist')
    search_fields = ('analysis_id', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = (
        'analysis_id', 'user', 'analysis_type', 'created_at',
        'original_image', 'face_url', 'scalp_url', 'segmentation_mask',
        'visualized_image', 'yolo_visualization', 'yolo_chart', 'efficientnet_visualization',
        'conditions', 'recommendations', 'recommendations_structured',
        'max_severity', 'severity_label', 'recommend_dermatologist',
    )
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False  # analyses are created only by the AI pipeline
