from core.models import AuditLog


# Paths whose POSTs are worth recording in the audit trail.
_AUDIT_PREFIXES = ("/dashboard/", "/accounts/login", "/accounts/register", "/orders/place")


class ActivityLogMiddleware:
    """Records mutating requests on sensitive paths to the AuditLog (best-effort)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if request.method == "POST" and request.path.startswith(_AUDIT_PREFIXES):
                AuditLog.log(request, action=f"POST {request.path}")
        except Exception:
            pass  # auditing must never break a request
        return response
