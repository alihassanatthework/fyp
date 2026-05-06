from rest_framework import serializers
from .models import AnalysisFeedback


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AnalysisFeedback
        fields = ('id', 'analysis', 'rating', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
