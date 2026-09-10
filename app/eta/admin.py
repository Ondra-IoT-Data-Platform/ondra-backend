from django.contrib import admin
from eta.models import ETAModelVersion, ETATripRecord


@admin.register(ETATripRecord)
class ETATripRecordAdmin(admin.ModelAdmin):
    list_display = [
        "dispatch",
        "organization",
        "actual_duration_minutes",
        "distance_km",
        "base_eta_minutes",
        "product_name",
        "hour_of_day",
        "day_of_week",
        "departed_at",
        "delivered_at",
        "created_at",
    ]
    list_filter = [
        "organization",
        "product_name",
        "day_of_week",
        "created_at",
    ]
    search_fields = [
        "dispatch__waybill_number",
        "product_name",
        "driver_id",
    ]
    readonly_fields = [
        "id",
        "dispatch",
        "organization",
        "distance_km",
        "base_eta_minutes",
        "hour_of_day",
        "day_of_week",
        "driver_id",
        "origin_terminal_id",
        "product_name",
        "quantity",
        "actual_duration_minutes",
        "departed_at",
        "delivered_at",
        "created_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        # Records are created automatically — not manually
        return False

    def has_delete_permission(self, request, obj=None):
        # Protect training data integrity
        return request.user.is_superuser


@admin.register(ETAModelVersion)
class ETAModelVersionAdmin(admin.ModelAdmin):
    list_display = [
        "version",
        "organization",
        "status",
        "records_used",
        "mae_minutes",
        "rmse_minutes",
        "mape_percentage",
        "trained_at",
        "created_at",
    ]
    list_filter = [
        "status",
        "organization",
        "trained_at",
    ]
    search_fields = [
        "organization__name",
        "version",
        "model_file_path",
    ]
    readonly_fields = [
        "id",
        "created_at",
    ]
    ordering = ["-version"]
    fieldsets = (
        ("Identity", {
            "fields": ("id", "organization", "version", "status"),
        }),
        ("Training Data", {
            "fields": ("records_used", "trained_at", "model_file_path"),
        }),
        ("Evaluation Metrics", {
            "fields": ("mae_minutes", "rmse_minutes", "mape_percentage"),
            "description": "Metrics computed on the held-out test set (30% of records)",
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # Only superuser can delete model versions
        return request.user.is_superuser
