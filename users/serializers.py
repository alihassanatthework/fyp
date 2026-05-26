import logging

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import UserProfile, MedicalHistory, UserRole

logger = logging.getLogger(__name__)

# Health condition strings sent from the React SignUp form → model field mapping
_HEALTH_CONDITION_MAP = {
    'Allergies': 'has_allergies',
    'Diabetes': 'is_diabetic',
    'Pregnancy': 'is_pregnant',
    'Heart-related condition': 'has_cardio_issues',
    'Other medical condition': None,  # stored in other_conditions text field
}


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    health_conditions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        try:
            validate_password(attrs['password'])
        except Exception as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        health_conditions = validated_data.pop('health_conditions', [])
        validated_data.pop('confirm_password')
        full_name = validated_data.pop('full_name').strip()
        email = validated_data['email']

        # Django's auth_user requires a username — we use email as username
        parts = full_name.split(' ', 1)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else '',
        )

        # Always create profile + medical history rows at registration
        UserProfile.objects.create(user=user)
        UserRole.objects.create(user=user, role='user')  # default role
        med = MedicalHistory.objects.create(user=user)

        other_conditions = []
        for cond in health_conditions:
            field = _HEALTH_CONDITION_MAP.get(cond)
            if field:
                setattr(med, field, True)
            elif cond not in ('None',):
                other_conditions.append(cond)

        if other_conditions:
            med.other_conditions = ', '.join(other_conditions)
        med.save()

        logger.info("Registered new user: %s", email)
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    member_since = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name', 'member_since')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

    def get_member_since(self, obj):
        return obj.date_joined.strftime("%B %Y")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('age', 'gender', 'skin_type', 'hair_type', 'updated_at')
        read_only_fields = ('updated_at',)


class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = (
            'is_pregnant', 'has_cardio_issues', 'is_diabetic',
            'has_allergies', 'has_hypertension', 'has_asthma',
            'has_skin_conditions', 'has_scalp_conditions',
            'other_conditions', 'current_medications', 'known_allergens',
        )
