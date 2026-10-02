from django.contrib import admin

from .models import Room, ShoppingList, ShoppingListItem


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0


class ItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 0
    fields = ("room", "title_snapshot", "bpid_snapshot", "variant_id_snapshot", "quantity", "price_snapshot", "status")
    readonly_fields = ("title_snapshot", "bpid_snapshot", "variant_id_snapshot", "price_snapshot")


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "owner", "client_name", "status", "updated_at")
    search_fields = ("code", "name", "client_name", "owner__username", "bilnov_project_id")
    list_filter = ("status",)
    readonly_fields = ("code",)
    inlines = [RoomInline, ItemInline]
