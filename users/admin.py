from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, MedicalHistory


class UserProfileInline(admin.StackedInline):
    model   = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class MedicalHistoryInline(admin.StackedInline):
    model   = MedicalHistory
    can_delete = False
    verbose_name_plural = 'Medical History'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, MedicalHistoryInline)
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    ordering = ('-date_joined',)


# Re-register User with our enhanced admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'skin_type', 'hair_type', 'gender', 'age', 'updated_at')
    search_fields = ('user__email', 'user__first_name')
    list_filter   = ('skin_type', 'hair_type', 'gender')


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display  = ('user', 'is_pregnant', 'is_diabetic', 'has_allergies', 'has_cardio_issues', 'updated_at')
    search_fields = ('user__email',)
    list_filter   = ('is_pregnant', 'is_diabetic', 'has_allergies', 'has_cardio_issues')
