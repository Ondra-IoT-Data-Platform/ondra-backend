import secrets
from uuid import UUID

from django.utils import timezone

from config.exceptions import BadRequestException, NotFoundException
from fleet.models import Truck, TruckStatusLog
from rfid_events.models import RFIDAlert, RFIDEvent, RFIDReaderStatus
from rfid_events.schema import (
    RFIDAlertOutSchema,
    RFIDAlertResolveSchema,
    RFIDEventInSchema,
    RFIDEventOutSchema,
    RFIDReaderStatusOutSchema,
    RFIDSimulateEventSchema,
)
from terminals.models import Gates
from users.models import User

SIGNAL_STRENGTH_THRESHOLD = -80.0


def _resolve_truck_status(direction: str) -> str:
    return "outbound" if direction == "exit" else "inbound"


def process_rfid_event_service(
    data: RFIDEventInSchema,
    organization_id: UUID,
) -> RFIDEventOutSchema:
    """
    Processes an inbound RFID gate event.
    Handles idempotency, signal filtering, truck resolution,
    status update, and unrecognized vehicle alert creation.
    Fully synchronous.
    """
    try:
        # Idempotency — discard duplicate message IDs
        already_processed = RFIDEvent.objects.filter(
            message_id=data.message_id
        ).exists()
        if already_processed:
            event = RFIDEvent.objects.select_related(
                "truck", "gate", "terminal"
            ).get(message_id=data.message_id)
            return RFIDEventOutSchema.from_orm(event)

        # Signal strength filter
        if (
            data.signal_strength is not None
            and data.signal_strength < SIGNAL_STRENGTH_THRESHOLD
        ):
            raise BadRequestException(
                f"Signal strength {data.signal_strength} dBm below "
                f"threshold {SIGNAL_STRENGTH_THRESHOLD} dBm — discarded"
            )

        # Resolve truck by RFID tag
        truck = None
        is_recognized = False
        status_triggered = None

        try:
            truck = Truck.objects.get(
                rfid_tag_id=data.raw_tag_id,
                organization_id=organization_id,
            )
            is_recognized = True
            status_triggered = _resolve_truck_status(data.direction)

            # Update truck status
            previous_status = truck.current_status
            truck.current_status = status_triggered
            truck.save()

            # Write audit log
            TruckStatusLog.objects.create(
                truck=truck,
                previous_status=previous_status,
                new_status=status_triggered,
                trigger_source=TruckStatusLog.TriggerSource.RFID,
                note=(
                    f"RFID gate {data.direction} at "
                    f"terminal {data.terminal_id} "
                    f"gate {data.gate_id}"
                ),
            )

        except Truck.DoesNotExist:
            is_recognized = False

        # Create event record
        event = RFIDEvent.objects.create(
            message_id=data.message_id,
            raw_tag_id=data.raw_tag_id,
            truck=truck,
            gate_id=data.gate_id,
            terminal_id=data.terminal_id,
            direction=data.direction,
            signal_strength=data.signal_strength,
            is_recognized=is_recognized,
            status_triggered=status_triggered,
            organization_id=organization_id,
            event_time=data.event_time,
        )

        # Raise alert for unrecognized tags
        if not is_recognized:
            RFIDAlert.objects.create(
                rfid_event=event,
                raw_tag_id=data.raw_tag_id,
                gate_id=data.gate_id,
                terminal_id=data.terminal_id,
                organization_id=organization_id,
            )

        # Reload with related fields for schema serialization
        event = RFIDEvent.objects.select_related(
            "truck", "gate", "terminal"
        ).get(id=event.id)

        return RFIDEventOutSchema.from_orm(event)

    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


def simulate_rfid_event_service(
    data: RFIDSimulateEventSchema,
    organization_id: UUID,
) -> RFIDEventOutSchema:
    """
    Simulates an RFID gate event for prototype demonstration.
    Fully synchronous.
    """
    try:
        # Get raw tag ID
        if data.simulate_unrecognized:
            raw_tag_id = f"SIM-UNRECOGNIZED-{secrets.token_hex(4)}"
        else:
            raw_tag_id = (
                Truck.objects.filter(id=data.truck_id)
                .values_list("rfid_tag_id", flat=True)
                .first()
            )
            if not raw_tag_id:
                raise BadRequestException(
                    f"Truck {data.truck_id} has no rfid_tag_id assigned. "
                    "Set one in Django admin before simulating."
                )

        # Get terminal ID from gate
        terminal_id = (
            Gates.objects.filter(id=data.gate_id)
            .values_list("terminal_id", flat=True)
            .first()
        )
        if not terminal_id:
            raise BadRequestException(
                f"Gate {data.gate_id} not found or has no terminal assigned."
            )

        synthetic_event = RFIDEventInSchema(
            message_id=f"SIM-{secrets.token_hex(8)}",
            raw_tag_id=raw_tag_id,
            gate_id=data.gate_id,
            terminal_id=terminal_id,
            direction=data.direction,
            signal_strength=-55.0,
            event_time=timezone.now(),
        )

        return process_rfid_event_service(synthetic_event, organization_id)

    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_rfid_events_service(
    organization_id: UUID,
    terminal_id: int | None = None,
    is_recognized: bool | None = None,
) -> list[RFIDEventOutSchema]:
    try:
        qs = RFIDEvent.objects.filter(
            organization_id=organization_id
        ).select_related(
            "truck", "gate", "terminal"
        ).order_by("-event_time")

        if terminal_id:
            qs = qs.filter(terminal_id=terminal_id)
        if is_recognized is not None:
            qs = qs.filter(is_recognized=is_recognized)

        return [RFIDEventOutSchema.from_orm(e) for e in qs]
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_rfid_alerts_service(
    organization_id: UUID,
    is_resolved: bool | None = None,
) -> list[RFIDAlertOutSchema]:
    try:
        qs = RFIDAlert.objects.filter(
            organization_id=organization_id
        ).select_related(
            "gate", "terminal", "resolved_by"
        ).order_by("-created_at")

        if is_resolved is not None:
            qs = qs.filter(is_resolved=is_resolved)

        return [RFIDAlertOutSchema.from_orm(a) for a in qs]
    except Exception as e:
        raise BadRequestException(str(e)) from e


def resolve_rfid_alert_service(
    alert_id: UUID,
    # organization_id: UUID,
    data: RFIDAlertResolveSchema,
    resolved_by_id: UUID,
) -> RFIDAlertOutSchema:
    try:
        alert = RFIDAlert.objects.select_related(
            "gate", "terminal", "resolved_by"
        ).get(id=alert_id)

        if alert.is_resolved:
            raise BadRequestException(
                "This alert has already been resolved"
            )
        user = User.objects.get(email=resolved_by_id)

        alert.is_resolved = True
        alert.resolution_note = data.resolution_note
        alert.resolved_by = user
        alert.resolved_at = timezone.now()
        alert.save()

        return RFIDAlertOutSchema.from_orm(alert)

    except RFIDAlert.DoesNotExist:
        raise NotFoundException("Alert not found")
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_reader_statuses_service(
    organization_id: UUID,
    terminal_id: int | None = None,
) -> list[RFIDReaderStatusOutSchema]:
    try:
        qs = RFIDReaderStatus.objects.filter(
            organization_id=organization_id
        ).select_related("gate", "terminal").order_by("reader_id")

        if terminal_id:
            qs = qs.filter(terminal_id=terminal_id)

        return [RFIDReaderStatusOutSchema.from_orm(r) for r in qs]
    except Exception as e:
        raise BadRequestException(str(e)) from e
