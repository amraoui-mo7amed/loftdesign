from django.contrib import admin

from .models import Category, Product, ProductAsset, ProductItem


class ProductAssetInline(admin.TabularInline):
    model = ProductAsset
    extra = 1
    fields = ("file_format", "variant", "file", "version", "is_current", "notes")
    readonly_fields = ("version", "is_current")


class ProductItemInline(admin.TabularInline):
    model = ProductItem
    extra = 0
    fields = ("name", "sku", "color", "dimensions", "stock_quantity", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("bilnov_object_id", "title", "category", "brand", "status", "model_version")
    search_fields = ("bilnov_object_id", "title", "sku", "brand", "collection", "items__sku")
    list_filter = ("status", "category")
    readonly_fields = ("bilnov_object_id", "bilnov_uuid", "model_version")
    inlines = [ProductItemInline, ProductAssetInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    list_editable = ("code",)


@admin.register(ProductAsset)
class ProductAssetAdmin(admin.ModelAdmin):
    list_display = ("product", "file_format", "version", "is_current", "created_at")
    list_filter = ("file_format", "is_current")
    search_fields = ("product__bilnov_object_id", "product__title")
