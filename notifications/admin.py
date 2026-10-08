from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "event", "recipient", "status")
    list_filter = ("channel", "status", "event")
    search_fields = ("recipient", "subject", "body")
    readonly_fields = [f.name for f in Notification._meta.fields]
