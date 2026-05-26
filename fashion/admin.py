from django.contrib import admin
from .models import FashionSuggestion


@admin.register(FashionSuggestion)
class FashionSuggestionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'event_type', 'body_type', 'skin_tone', 'created_at')
    list_filter   = ('event_type', 'body_type', 'skin_tone')
    search_fields = ('user__email',)
