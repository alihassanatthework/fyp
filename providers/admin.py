from django.contrib import admin
from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display  = ('name', 'provider_type', 'city', 'phone', 'is_active')
    list_filter   = ('provider_type', 'city', 'is_active')
    search_fields = ('name', 'city', 'address')
    list_editable = ('is_active',)
