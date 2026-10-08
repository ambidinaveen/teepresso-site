"""Expose business rules + safe-mode integration flags to every template."""
from django.conf import settings


def site_flags(request):
    return {
        "RULES": settings.TEEPRESSO,
        "FLAGS": settings.INTEGRATIONS,
        "BRAND": "Teepresso",
    }
