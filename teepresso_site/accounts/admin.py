from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTP, Address, User, WishlistItem


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "role", "phone", "company", "is_blocked", "is_active")
    list_filter = ("role", "is_blocked", "is_active", "is_staff")
    search_fields = ("email", "username", "phone", "company", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Teepresso", {"fields": ("role", "phone", "company", "gst_number", "is_blocked")}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "city", "state", "pincode", "is_default")
    search_fields = ("user__email", "city", "pincode")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("identifier", "purpose", "code", "used", "created_at")
    list_filter = ("purpose", "used")
