from users.models import User, UserProfile, DriverProfile, OfficeProfile
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet
from typing import Any



# class RoleAdmin(admin.ModelAdmin):
#     list_display = ["id", "name", "organization", "created_at"]
#     search_fields = ("name",)
#     list_filter = ["organization"]
#     ordering = ("-created_at",)
#     actions = ["make_inactive"]

#     def make_inactive(self, request: Any, queryset: QuerySet[Role]) -> None:
#         queryset.update(is_active=False)

#     make_inactive.short_description = "Mark selected roles as inactive"



class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "is_active", "is_staff", "is_superuser"]
    search_fields = ("email",)
    list_filter = ["is_active", "is_staff", "is_superuser"]
    ordering = ("-id",)
    actions = ["make_inactive"]

    def make_inactive(self, request: Any, queryset: QuerySet[User]) -> None:
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected users as inactive"



class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "fullname", "job_title", "created_at"]
    search_fields = ("user__email",)
    list_filter = ["created_at"]
    ordering = ("-created_at",)


class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "license_number", "ops_location", "created_at"]
    search_fields = ("license_number", "ops_location")
    list_filter = ["created_at"]
    ordering = ("-created_at",)


class OfficeProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "created_at"]
    search_fields = ("department",)
    list_filter = ["created_at"]
    ordering = ("-created_at",)


# admin.site.register(Role, RoleAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(DriverProfile, DriverProfileAdmin)
admin.site.register(OfficeProfile, OfficeProfileAdmin)
