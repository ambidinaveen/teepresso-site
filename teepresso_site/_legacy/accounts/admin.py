from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Customer, Attendance


@admin.register(User)
class TeepressoUserAdmin(UserAdmin):
    list_display = ("username", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Teepresso", {"fields": ("role",)}),)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "whatsapp_verified", "created_at")
    search_fields = ("name", "phone")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "login_ts", "logout_ts", "status")
    list_filter = ("user",)
