from django.contrib import admin

from .models import (
    Order,
    OrderItem,
    OrderStatusEvent,
    Mockup,
    PaymentRecord,
    Shipment,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class EventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_no", "customer", "channel", "qty_total", "total",
        "status", "payment_status", "urgent", "created_at",
    )
    list_filter = ("status", "payment_status", "channel", "urgent")
    search_fields = ("order_no", "customer__name", "customer__phone")
    inlines = [OrderItemInline, EventInline]


admin.site.register(Mockup)
admin.site.register(PaymentRecord)
admin.site.register(Shipment)
