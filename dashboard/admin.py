from django.contrib import admin

from .models import Category, Manufacturer, Product, ProductAsset, ProductItem


class ProductAssetInline(admin.TabularInline):
    model = ProductAsset
    extra = 1
    fields = ("file_format", "variant", "file", "unit", "scale", "polygon_count", "compatibility", "version", "is_current", "notes")
    readonly_fields = ("version", "is_current")


class ProductItemInline(admin.TabularInline):
    model = ProductItem
    extra = 0
    fields = ("variant_id", "name", "sku", "manufacturer_reference", "color", "dimensions", "stock_quantity", "is_active")
    readonly_fields = ("variant_id",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("bpid", "title", "category", "brand", "manufacturer", "status", "model_version")
    search_fields = ("bpid", "title", "sku", "brand", "collection", "manufacturer_reference", "items__sku", "items__variant_id")
    list_filter = ("status", "category")
    readonly_fields = ("bpid", "bilnov_uuid", "model_version")
    inlines = [ProductItemInline, ProductAssetInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    list_editable = ("code",)


@admin.register(ProductAsset)
class ProductAssetAdmin(admin.ModelAdmin):
    list_display = ("product", "file_format", "version", "is_current", "unit", "polygon_count", "file_size", "created_at")
    list_filter = ("file_format", "is_current")
    readonly_fields = ("version", "is_current", "file_size", "sha256")
    search_fields = ("product__bpid", "product__title")


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ("manufacturer_id", "name", "country", "website")
    search_fields = ("manufacturer_id", "name")
    readonly_fields = ("manufacturer_id",)
