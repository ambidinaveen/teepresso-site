from django.contrib import admin

from .models import CorporateLead


@admin.register(CorporateLead)
class CorporateLeadAdmin(admin.ModelAdmin):
    list_display = ("company_name", "contact_person", "quantity", "status",
                    "assigned_to", "created_at")
    list_filter = ("status",)
    search_fields = ("company_name", "contact_person", "email", "phone")
    list_editable = ("status", "assigned_to")
