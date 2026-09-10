import uuid

from django.db import models
from django.utils import timezone

from organization.models import Organizations
from terminals.models import Gates, Terminals


class RFIDEvent(models.Model):
    """
    An event logged when a truck's RFID tag is detected at a gate.
    Created automatically by the MQTT subscriber service.
    Triggers truck status updates and dispatch status changes.
    """

    class Direction(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique MQTT message ID — used for idempotency deduplication",
    )
    raw_tag_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Raw EPC tag ID read by the RFID reader",
    )
    truck = models.ForeignKey(
        "fleet.Truck",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfid_events",
        help_text="Resolved truck — null if tag was unrecognized",
    )
    gate = models.ForeignKey(
        Gates,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfid_events",
    )
    terminal = models.ForeignKey(
        Terminals,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfid_events",
    )
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
    )
    signal_strength = models.FloatField(
        null=True,
        blank=True,
        help_text="RSSI signal strength in dBm — used to filter weak reads",
    )
    is_recognized = models.BooleanField(
        default=True,
        help_text="False if tag was not found in fleet registry",
    )
    status_triggered = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Truck status that was set as a result of this event",
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="rfid_events",
    )
    event_time = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Timestamp of when the tag was detected at the reader",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-event_time"]
        indexes = [
            models.Index(fields=["raw_tag_id"]),
            models.Index(fields=["event_time"]),
            models.Index(fields=["is_recognized"]),
            models.Index(fields=["organization", "event_time"]),
        ]

    def __str__(self) -> str:
        truck = self.truck.plate_number if self.truck else "Unknown"
        return f"{truck} — {self.direction} — {self.event_time}"


class RFIDAlert(models.Model):
    """
    Raised when an unrecognized RFID tag is detected at a gate.
    Terminal Head is notified immediately via WebSocket and SMS.
    Requires manual resolution by authorized personnel.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rfid_event = models.OneToOneField(
        RFIDEvent,
        on_delete=models.CASCADE,
        related_name="alert",
        help_text="The RFID event that triggered this alert",
    )
    raw_tag_id = models.CharField(
        max_length=100,
        db_index=True,
    )
    gate = models.ForeignKey(
        Gates,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    terminal = models.ForeignKey(
        Terminals,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="rfid_alerts",
    )
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolution_note = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_rfid_alerts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "Resolved" if self.is_resolved else "Unresolved"
        return f"Alert — {self.raw_tag_id} — {status}"


class RFIDReaderStatus(models.Model):
    """
    Tracks the last known heartbeat state of each RFID reader.
    Updated every time a heartbeat MQTT message is received.
    One row per reader — updated in place.
    If last_heartbeat exceeds 180 seconds, reader is considered offline.
    """

    class ReaderStatus(models.TextChoices):
        ONLINE = "online", "Online"
        DEGRADED = "degraded", "Degraded"
        OFFLINE = "offline", "Offline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique reader identifier matching MQTT client ID",
    )
    gate = models.OneToOneField(
        Gates,
        on_delete=models.CASCADE,
        related_name="reader_status",
        null=True,
        blank=True,
    )
    terminal = models.ForeignKey(
        Terminals,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reader_statuses",
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="reader_statuses",
    )
    status = models.CharField(
        max_length=20,
        choices=ReaderStatus.choices,
        default=ReaderStatus.ONLINE,
    )
    firmware_version = models.CharField(max_length=20, blank=True, null=True)
    uptime_seconds = models.PositiveIntegerField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["reader_id"]

    def __str__(self) -> str:
        return f"{self.reader_id} — {self.status}"
