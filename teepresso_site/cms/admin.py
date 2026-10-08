from django.contrib import admin

from .models import (Banner, ContactMessage, FAQ, Newsletter, Page,
                     SiteSetting, Testimonial)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "sort", "active")
    list_editable = ("sort", "active")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "sort", "active")
    list_filter = ("category", "active")
    list_editable = ("sort", "active")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "rating", "is_corporate", "active")
    list_filter = ("is_corporate", "active")


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "active", "updated_at")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "handled", "created_at")
    list_filter = ("handled",)
    list_editable = ("handled",)


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value")
