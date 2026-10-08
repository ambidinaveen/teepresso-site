from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "ip", "path")
    list_filter = ("action",)
    search_fields = ("action", "detail", "path")
    readonly_fields = ("user", "action", "detail", "ip", "path", "created_at")
