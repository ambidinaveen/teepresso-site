from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "amount", "status", "upi_ref", "created_at")
    list_filter = ("status", "method")
    search_fields = ("order__order_no", "gateway_payment_id", "upi_ref")
