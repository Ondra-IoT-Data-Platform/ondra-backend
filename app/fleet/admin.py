from django.contrib import admin

from fleet.models import (
    Product,
    Route,
    Truck,
    TruckLocation,
    TruckStatusLog,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "unit",
        "organization",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "organization",
        "unit",
    )

    search_fields = (
        "name",
        "description",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("name",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        "route_name",
        "origin_terminal",
        "destination",
        "standard_distance_km",
        "expected_tat_hours",
        "organization",
        "created_at",
    )

    list_filter = (
        "organization",
        "origin_terminal",
    )

    search_fields = (
        "route_name",
        "destination",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("route_name",)


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        "plate_number",
        "truck_type",
        "capacity",
        "current_status",
        "default_product",
        "home_terminal",
        "rfid_tag_id",
        "is_active",
        "organization",
        "created_at",
    )

    list_filter = (
        "truck_type",
        "current_status",
        "is_active",
        "organization",
        "home_terminal",
    )

    search_fields = [
        'plate_number',
        'driver__email',
        'driver__first_name',
        'driver__last_name'
    ]

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "default_product",
        "home_terminal",
        "organization",
    )

    ordering = ("plate_number",)


@admin.register(TruckLocation)
class TruckLocationAdmin(admin.ModelAdmin):
    list_display = (
        "truck",
        "latitude",
        "longitude",
        "speed_kmh",
        "bearing",
        "provider",
        "last_synced",
    )

    list_filter = (
        "provider",
    )

    search_fields = (
        "truck__plate_number",
        "latitude",
        "longitude",
        "provider",
    )

    readonly_fields = (
        "last_synced",
    )

    autocomplete_fields = (
        "truck",
    )

    ordering = ("-last_synced",)


@admin.register(TruckStatusLog)
class TruckStatusLogAdmin(admin.ModelAdmin):
    list_display = (
        "truck",
        "previous_status",
        "new_status",
        "trigger_source",
        "triggered_by",
        "note",
        "created_at",
    )

    list_filter = (
        "previous_status",
        "new_status",
        "trigger_source",
    )

    search_fields = (
        "truck__plate_number",
        "triggered_by__username",
        "note",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    autocomplete_fields = (
        "truck",
        "triggered_by",
    )

    ordering = ("-created_at",)
