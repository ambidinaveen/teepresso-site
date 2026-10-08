from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from accounts.models import User


def staff_required(view):
    """Allow only staff roles into the dashboard (RBAC)."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (u.is_superuser or u.is_staff_role):
            raise PermissionDenied("You don't have access to the dashboard.")
        return view(request, *args, **kwargs)
    return _wrapped


def role_required(*roles):
    """Restrict a view to specific staff roles (super_admin always allowed)."""
    allowed = set(roles) | {User.Role.SUPER_ADMIN}

    def deco(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not (u.is_superuser or u.role in allowed):
                raise PermissionDenied("Insufficient role for this section.")
            return view(request, *args, **kwargs)
        return _wrapped
    return deco
