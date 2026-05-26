from rest_framework import serializers
from .models import Booking
from providers.serializers import ProviderSerializer


class BookingSerializer(serializers.ModelSerializer):
    provider_detail = ProviderSerializer(source='provider', read_only=True)

    class Meta:
        model  = Booking
        fields = ['id', 'provider', 'provider_detail', 'date', 'time', 'notes', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']
