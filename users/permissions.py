"""
users/permissions.py
─────────────────────
Two roles: admin and user.
All AI outputs are automated — no expert/dermatologist/salon role needed.
"""
from rest_framework.permissions import BasePermission


def _get_role(user) -> str:
    try:
        return user.role.role
    except Exception:
        return 'user'


class IsAdmin(BasePermission):
    """Admin only — user management, system monitoring via Django admin."""
    message = 'Admin access required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_role(request.user) == 'admin'


class IsOwnerOrAdmin(BasePermission):
    """Object-level: allow if user owns the object or is admin."""
    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj):
        if _get_role(request.user) == 'admin':
            return True
        return getattr(obj, 'user', None) == request.user
