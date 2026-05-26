from django.db import models
from django.contrib.auth.models import User
from core.encryption.fields import EncryptedTextField


class UserRole(models.Model):
    """
    Two roles only:
      - user  → end user (all app features)
      - admin → Django admin panel, user management, system monitoring
    All AI decisions (diagnosis, recommendations, bookings) are fully automated.
    """
    ROLES = [
        ('user',  'User'),
        ('admin', 'Admin'),
    ]
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role')
    role       = models.CharField(max_length=10, choices=ROLES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.role}"

    @property
    def is_admin(self):
        return self.role == 'admin'


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], null=True, blank=True)
    skin_type = models.CharField(max_length=20, choices=[
        ('oily', 'Oily'),
        ('dry', 'Dry'),
        ('combination', 'Combination'),
        ('normal', 'Normal'),
        ('sensitive', 'Sensitive'),
    ], null=True, blank=True)
    hair_type = models.CharField(max_length=20, choices=[
        ('straight', 'Straight'),
        ('wavy', 'Wavy'),
        ('curly', 'Curly'),
        ('coily', 'Coily'),
    ], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class MedicalHistory(models.Model):
    """User medical history for personalized treatment recommendations"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medical_history')
    
    # Medical conditions
    is_pregnant = models.BooleanField(default=False, help_text="Currently pregnant")
    has_cardio_issues = models.BooleanField(default=False, help_text="Cardiovascular/heart issues")
    is_diabetic = models.BooleanField(default=False, help_text="Diabetes")
    has_allergies = models.BooleanField(default=False, help_text="Allergies to medications/products")
    has_hypertension = models.BooleanField(default=False, help_text="High blood pressure")
    has_asthma = models.BooleanField(default=False, help_text="Asthma")
    has_skin_conditions = models.BooleanField(default=False, help_text="Existing skin conditions")
    has_scalp_conditions = models.BooleanField(default=False, help_text="Existing scalp conditions")
    
    # Additional notes — encrypted at rest
    other_conditions    = EncryptedTextField(blank=True, null=True, help_text="Other medical conditions or notes")
    current_medications = EncryptedTextField(blank=True, null=True, help_text="Current medications")
    known_allergens     = EncryptedTextField(blank=True, null=True, help_text="Known allergens (if any)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Medical History"
    
    def get_active_conditions(self):
        """Get list of active medical conditions"""
        conditions = []
        if self.is_pregnant:
            conditions.append('Pregnancy')
        if self.has_cardio_issues:
            conditions.append('Cardiovascular Issues')
        if self.is_diabetic:
            conditions.append('Diabetes')
        if self.has_allergies:
            conditions.append('Allergies')
        if self.has_hypertension:
            conditions.append('Hypertension')
        if self.has_asthma:
            conditions.append('Asthma')
        return conditions
