from django.contrib import admin
from access.models import OrganizationTokens, UserSession


class OrganizationTokensAdmin(admin.ModelAdmin):
    list_display = ("id", "token", "token_type", "user", "organization", "is_used", "expires_at")
    search_fields = ("token_type", "user__email", "organization__name", "token")
    list_filter = ("token_type", "is_used")



class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "expires_at")
    search_fields = ("user__email",)
    list_filter = ("created_at", "expires_at")



admin.site.register(OrganizationTokens, OrganizationTokensAdmin)
admin.site.register(UserSession, UserSessionAdmin)
