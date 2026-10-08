from django.contrib import admin

from .models import Invoice, Order, OrderItem, OrderStatusEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "name", "variant_label", "qty", "unit_price")


class StatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = ("status", "note", "actor", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "full_name", "status", "payment_status", "total",
                    "eway_required", "created_at")
    list_filter = ("status", "payment_status", "eway_required")
    search_fields = ("order_no", "full_name", "phone", "email")
    inlines = [OrderItemInline, StatusEventInline]
    readonly_fields = ("order_no", "created_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "order", "created_at")
