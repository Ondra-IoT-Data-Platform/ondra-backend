from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from rfid_events.models import RFIDAlert, RFIDEvent, RFIDReaderStatus


class RFIDEventInSchema(Schema):
    """
    Payload published by RFID edge sensor via MQTT.
    Received by the MQTT subscriber and passed to the processing service.
    """
    message_id: str
    raw_tag_id: str
    gate_id: int
    terminal_id: int
    direction: str
    signal_strength: Optional[float] = None
    event_time: datetime


class RFIDEventOutSchema(ModelSchema):
    class Meta:
        model = RFIDEvent
        fields = [
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


class RFIDAlertOutSchema(ModelSchema):
    """RFID alert output."""
    class Meta:
        model = RFIDAlert
        fields = [
            "id", "rfid_event", "raw_tag_id", "gate",
            "terminal", "organization", "is_resolved",
            "resolution_note", "resolved_by",
            "resolved_at", "created_at",
        ]


class RFIDAlertResolveSchema(Schema):
    """Resolves an unrecognized vehicle alert."""
    resolution_note: str


class RFIDReaderStatusOutSchema(ModelSchema):
    """Reader heartbeat status output."""
    class Meta:
        model = RFIDReaderStatus
        fields = [
            "id", "reader_id", "gate", "terminal",
            "organization", "status", "firmware_version",
            "uptime_seconds", "last_heartbeat", "updated_at",
        ]


class RFIDSimulateEventSchema(Schema):
    """
    Simulates an RFID gate event for prototype demonstration.
    Only available in non-production environments.
    """
    truck_id: UUID
    gate_id: int
    direction: str
    simulate_unrecognized: bool = False
