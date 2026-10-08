"""Capture staff login/logout times for the attendance sheet (REQ-ATT-1)."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import Attendance


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    Attendance.objects.create(user=user)


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    if user is None:
        return
    last = (
        Attendance.objects.filter(user=user, logout_ts__isnull=True)
        .order_by("-login_ts")
        .first()
    )
    if last:
        last.logout_ts = timezone.now()
        last.save(update_fields=["logout_ts"])
