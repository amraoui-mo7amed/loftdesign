from django.contrib import admin

from .models import ApiClient


@admin.register(ApiClient)
class ApiClientAdmin(admin.ModelAdmin):
    list_display = ("name", "prefix", "is_active", "created_at", "last_used_at")
    readonly_fields = ("prefix", "created_at", "last_used_at")

    def has_add_permission(self, request):
        return False  # keys are created with: python manage.py api_key create "BILNOV Desktop"
