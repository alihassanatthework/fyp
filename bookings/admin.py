from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ('user', 'provider', 'date', 'time', 'status', 'created_at')
    list_filter   = ('status', 'provider__provider_type', 'date')
    search_fields = ('user__email', 'provider__name')
    list_editable = ('status',)
