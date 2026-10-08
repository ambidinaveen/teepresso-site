from django.contrib import admin

from .models import WhatsAppMessage


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ("order", "phone", "kind", "status", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("phone", "order__order_no")
