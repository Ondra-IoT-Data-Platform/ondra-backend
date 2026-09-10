from uuid import UUID

from ninja import Router

from access.auth_utils import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    NotFoundException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response, BaseResponseSchema
from rfid_events.schema import (
    RFIDAlertResolveSchema,
    RFIDEventInSchema,
    RFIDSimulateEventSchema,
)
from rfid_events.services import (
    list_reader_statuses_service,
    list_rfid_alerts_service,
    list_rfid_events_service,
    process_rfid_event_service,
    resolve_rfid_alert_service,
    simulate_rfid_event_service,
)
from organization.models import OrganizationMember


R = OrganizationMember.RoleChoices

router = Router(tags=["RFID"], auth=JWTAuthBearer())

RFID_VIEWERS = [
    R.ORG_ADMIN, R.MANAGEMENT,
    R.LOGISTICS_OFFICER, R.TRACKING_OFFICER,
]
ALERT_RESOLVERS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER]


@router.post("/rfid/events")
def receive_rfid_event(
    org_id: UUID,
    request, data: RFIDEventInSchema
) -> BaseResponseSchema:
    """
    Receives a gate event from the RFID edge sensor via MQTT subscriber.
    Handles idempotency, signal filtering, truck resolution, and alert creation.
    This endpoint is called by the internal MQTT subscriber service — not by users.
    """
    try:
        result = process_rfid_event_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/rfid/events")
@require_roles(*RFID_VIEWERS)
def list_rfid_events(
    request,
    org_id: UUID,
    terminal_id: int | None = None,
    is_recognized: bool | None = None,
) -> BaseResponseSchema:
    """
    Lists RFID gate events.
    Optional filters: ?terminal_id=1, ?is_recognized=false
    """
    try:
        result = list_rfid_events_service(
            org_id, terminal_id, is_recognized
        )
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/rfid/alerts")
def list_rfid_alerts(
    request,
    org_id: UUID,
    is_resolved: bool | None = None,
) -> BaseResponseSchema:
    """
    Lists unrecognized vehicle alerts.
    Optional filter: ?is_resolved=false
    """
    try:
        result = list_rfid_alerts_service(org_id, is_resolved)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/rfid/alerts/{alert_id}/resolve")
@require_roles(*ALERT_RESOLVERS)
def resolve_rfid_alert(
    request, alert_id: UUID, data: RFIDAlertResolveSchema
) -> BaseResponseSchema:
    """Resolves an unrecognized vehicle alert."""
    try:
        user_id = request.auth
        result = resolve_rfid_alert_service(
            alert_id, data, user_id
        )
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/rfid/readers")
@require_roles(*RFID_VIEWERS)
def list_reader_statuses(
    request,
    org_id: UUID,
    terminal_id: int | None = None,
) -> dict:
    """
    Lists RFID reader heartbeat statuses.
    Optional filter: ?terminal_id=1
    """
    try:
        result = list_reader_statuses_service(org_id, terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.post("/rfid/simulate")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER)
def simulate_rfid_event(
    request,
    org_id: UUID,
    data: RFIDSimulateEventSchema
) -> dict:
    """
    Simulates an RFID gate event for prototype demonstration.
    Exercises the full processing flow with synthetic data.
    """
    try:
        result = simulate_rfid_event_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
