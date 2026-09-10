# rfid/admin.py

from django.contrib import admin
from django.utils import timezone
from rfid_events.models import RFIDAlert, RFIDEvent, RFIDReaderStatus


@admin.register(RFIDEvent)
class RFIDEventAdmin(admin.ModelAdmin):
    list_display = [
        "message_id",
        "raw_tag_id",
        "truck",
        "gate",
        "terminal",
        "direction",
        "signal_strength",
        "is_recognized",
        "status_triggered",
        "event_time",
        "created_at",
    ]
    list_filter = [
        "direction",
        "is_recognized",
        "terminal",
        "organization",
        "event_time",
    ]
    search_fields = [
        "message_id",
        "raw_tag_id",
        "truck__plate_number",
    ]
    readonly_fields = [
        "id",
        "message_id",
        "raw_tag_id",
        "truck",
        "gate",
        "terminal",
        "direction",
        "signal_strength",
        "is_recognized",
        "status_triggered",
        "organization",
        "event_time",
        "created_at",
    ]
    ordering = ["-event_time"]
    date_hierarchy = "event_time"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(RFIDAlert)
class RFIDAlertAdmin(admin.ModelAdmin):
    list_display = [
        "raw_tag_id",
        "gate",
        "terminal",
        "organization",
        "is_resolved",
        "resolved_by",
        "resolved_at",
        "created_at",
    ]
    list_filter = [
        "is_resolved",
        "terminal",
        "organization",
        "created_at",
    ]
    search_fields = [
        "raw_tag_id",
        "resolution_note",
    ]
    readonly_fields = [
        "id",
        "rfid_event",
        "raw_tag_id",
        "gate",
        "terminal",
        "organization",
        "created_at",
    ]
    ordering = ["-created_at"]
    fieldsets = (
        ("Event Details", {
            "fields": (
                "id", "rfid_event", "raw_tag_id",
                "gate", "terminal", "organization", "created_at",
            ),
        }),
        ("Resolution", {
            "fields": (
                "is_resolved", "resolution_note",
                "resolved_by", "resolved_at",
            ),
        }),
    )

    actions = ["mark_resolved"]

    def mark_resolved(self, request, queryset):
        queryset.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now(),
            resolution_note="Bulk resolved via admin action",
        )
        self.message_user(
            request,
            f"{queryset.count()} alert(s) marked as resolved."
        )
    mark_resolved.short_description = "Mark selected alerts as resolved"


@admin.register(RFIDReaderStatus)
class RFIDReaderStatusAdmin(admin.ModelAdmin):
    list_display = [
        "reader_id",
        "gate",
        "terminal",
        "organization",
        "status",
        "firmware_version",
        "uptime_seconds",
        "last_heartbeat",
        "updated_at",
    ]
    list_filter = [
        "status",
        "terminal",
        "organization",
    ]
    search_fields = [
        "reader_id",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "last_heartbeat",
    ]
    ordering = ["reader_id"]
    fieldsets = (
        ("Identity", {
            "fields": (
                "id", "reader_id", "gate",
                "terminal", "organization",
            ),
        }),
        ("Status", {
            "fields": (
                "status", "firmware_version",
                "uptime_seconds", "last_heartbeat",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )
