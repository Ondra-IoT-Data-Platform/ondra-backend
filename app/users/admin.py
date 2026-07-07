from users.models import Role, User, UserProfile, DriverProfile, OfficeProfile
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet
from typing import Any


admin.site.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "organization", "created_at"]
    search_fields = ("name",)
    list_filter = ["organization"]
    ordering = ("-created_at",)
    actions = ["make_inactive"]

    def make_inactive(self, request: Any, queryset: QuerySet[Role]) -> None:
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected roles as inactive"


admin.site.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "full_name", "is_active", "is_staff", "is_superuser"]
    search_fields = ("email", "full_name")
    list_filter = ["is_active", "is_staff", "is_superuser"]
    ordering = ("-id",)
    actions = ["make_inactive"]

    def make_inactive(self, request: Any, queryset: QuerySet[User]) -> None:
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected users as inactive"


admin.site.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "license_number", "ops_location", "created_at"]
    search_fields = ("license_number", "ops_location")
    list_filter = ["created_at"]
    ordering = ("-created_at",)

admin.site.register(OfficeProfile)
class OfficeProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "department", "created_at"]
    search_fields = ("department",)
    list_filter = ["created_at"]
    ordering = ("-created_at",)
