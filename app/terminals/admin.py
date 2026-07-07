from terminals.models import Terminals, Gates
from django.contrib import admin
from django.db.models.query import QuerySet
from typing import Any

admin.site.register(Terminals)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "organization", "created_at"]
    search_fields = ("name",)
    list_filter = ["organization"]
    ordering = ("-created_at",)
    actions = ["make_inactive"]

    def make_inactive(self, request: Any, queryset: QuerySet[Terminals]) -> None:
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected terminals as inactive"


admin.site.register(Gates)
class GateAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "terminal", "gate_type"]
    search_fields = ("name",)
    list_filter = ["terminal", "gate_type"]
    ordering = ("-id",)
    actions = ["make_inactive"]

    def make_inactive(self, request: Any, queryset: QuerySet[Gates]) -> None:
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected gates as inactive"
