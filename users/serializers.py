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
    """
    Accepts EITHER:
      • Option A (legacy): full_name + confirm_password
      • Option B (current React form): first_name + last_name
    Both shapes resolve to a User with first_name + last_name set.
    """
    full_name        = serializers.CharField(required=False, max_length=150, allow_blank=True)
    first_name       = serializers.CharField(required=False, max_length=150, allow_blank=True)
    last_name        = serializers.CharField(required=False, max_length=150, allow_blank=True)
    email            = serializers.EmailField(required=True)
    password         = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    health_conditions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    account_type = serializers.ChoiceField(
        choices=['free', 'premium'], required=False, default='free'
    )

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        # Must have at least one of full_name OR first_name
        if not attrs.get('full_name') and not attrs.get('first_name'):
            raise serializers.ValidationError({"first_name": "First name is required."})
        # confirm_password is optional; check only if it was sent
        cp = attrs.get('confirm_password')
        if cp and attrs['password'] != cp:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        try:
            validate_password(attrs['password'])
        except Exception as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        health_conditions = validated_data.pop('health_conditions', [])
        account_type = validated_data.pop('account_type', 'free')
        validated_data.pop('confirm_password', None)

        # Resolve first/last from either input shape
        first_name = (validated_data.pop('first_name', '') or '').strip()
        last_name  = (validated_data.pop('last_name',  '') or '').strip()
        full_name  = (validated_data.pop('full_name',  '') or '').strip()
        if not first_name and full_name:
            parts = full_name.split(' ', 1)
            first_name = parts[0]
            last_name  = parts[1] if len(parts) > 1 else last_name

        email = validated_data['email']

        # Django's auth_user requires a username — we use email as username
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name,
        )

        # Always create profile + medical history rows at registration
        UserProfile.objects.create(user=user, account_type=account_type)
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
    # Expose raw ISO date_joined so the frontend can format it as needed
    # (Profile page now displays "Month DD, YYYY").
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name',
                  'member_since', 'date_joined')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

    def get_member_since(self, obj):
        return obj.date_joined.strftime("%B %Y")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('age', 'gender', 'skin_type', 'hair_type', 'account_type', 'updated_at')
        read_only_fields = ('account_type', 'updated_at')
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
