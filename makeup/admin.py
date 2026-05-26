from django.contrib import admin
from .models import MakeupSuggestion


@admin.register(MakeupSuggestion)
class MakeupSuggestionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'face_shape', 'skin_tone', 'created_at')
    list_filter   = ('face_shape', 'skin_tone')
    search_fields = ('user__email',)
