from django.contrib import admin
from .models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'category', 'title', 'order', 'created_at')
    list_filter   = ('category',)
    search_fields = ('user__email', 'title', 'description')
    ordering      = ('order', '-created_at')
