"""Server-side RBAC (NFR-Security-1). Every panel view is guarded here."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required(login_url="/panel/login/")
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or getattr(user, "role", None) in roles:
                return view(request, *args, **kwargs)
            raise PermissionDenied("Your role cannot access this page.")
        return _wrapped
    return decorator
