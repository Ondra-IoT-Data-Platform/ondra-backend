from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet

from app.organization.models import Organizations


@admin.register(Organizations)
class OrganizationsAdmin(admin.ModelAdmin):  # type = ignore[type-arg]
    list_display = ["id", "name", "is_active", "industry", "created_at"]
    search_fields = ("name",)
    list_filter = ["is_active", "industry"]
    ordering = ("-created_at",)
    actions = ["make_inactive"]

    def make_inactive(self, request: Any, queryset: QuerySet[Organizations]) -> None:
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected organizations as inactive"
