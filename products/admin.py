from django.contrib import admin

from .models import (Brand, Category, CustomDesign, Inventory, Product,
                     ProductImage, ProductVariant, ProductVideo, Review)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "sort", "active")
    list_filter = ("active", "parent")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "base_price", "sale_price", "featured",
                    "best_seller", "sold_count", "active")
    list_filter = ("category", "active", "featured", "trending", "best_seller", "is_customizable")
    search_fields = ("name", "sku", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("featured", "best_seller", "active")
    inlines = [ProductImageInline, ProductVideoInline, ProductVariantInline, InventoryInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "rating", "approved", "created_at")
    list_filter = ("approved", "rating")
    list_editable = ("approved",)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "low_stock_threshold", "updated_at")


@admin.register(CustomDesign)
class CustomDesignAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "user", "status", "print_position", "created_at")
    list_filter = ("status",)
    list_editable = ("status",)
