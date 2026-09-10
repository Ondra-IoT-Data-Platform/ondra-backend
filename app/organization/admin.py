from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet

from organization.models import Organizations, OrganizationMember, OrganizationSettings


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



@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ["id", "user__email", "role", "joined_at"]
    search_fields = ("user__email",)
    list_filter = ["is_active"]
    ordering = ("-joined_at",)
