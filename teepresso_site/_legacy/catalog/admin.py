from django.contrib import admin

from .models import Quality, Color, Size, Product, PricingTier


@admin.register(Quality)
class QualityAdmin(admin.ModelAdmin):
    list_display = ("name", "gsm", "price_delta", "active")
    list_editable = ("price_delta", "active")


@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    list_display = ("min_qty", "unit_price")
    list_editable = ("unit_price",)


admin.site.register(Color)
admin.site.register(Size)
admin.site.register(Product)
