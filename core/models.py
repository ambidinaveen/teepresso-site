from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Security/activity audit trail (PRINTPROX: Audit Logs, Activity Monitoring)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=120)
    detail = models.CharField(max_length=300, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.user.get_username() if self.user else "anon"
        return f"{who} · {self.action}"

    @classmethod
    def log(cls, request, action, detail=""):
        user = getattr(request, "user", None)
        cls.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action,
            detail=detail[:300],
            ip=_client_ip(request),
            path=request.path[:200],
        )


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
