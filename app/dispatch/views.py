# dispatch/views.py
from uuid import UUID

from ninja import Router

from access.auth_utils import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response, BaseResponseSchema
from dispatch.schema import (
    DeliveryConfirmationCreateSchema,
    DispatchCreateSchema,
    DispatchStatusUpdateSchema,
    DispatchUpdateSchema,
    DriverArrivalSchema,
    ResendOTPSchema,
    TripMetadataCreateSchema,
    TripMetadataUpdateSchema,
    DispatchOutSchema,
    DispatchListOutSchema,
    DispatchStatusLogOutSchema,
    DeliveryConfirmationOutSchema,
    TripMetadataOutSchema,
)
from dispatch.services import (
    cancel_dispatch_service,
    confirm_delivery_service,
    create_dispatch_service,
    create_trip_metadata_service,
    driver_arrival_service,
    get_dispatch_service,
    # get_dispatch_status_history_service,
    get_trip_metadata_service,
    list_dispatches_service,
    resend_otp_service,
    update_dispatch_service,
    update_dispatch_status_service,
    update_trip_metadata_service,
)
from organization.models import OrganizationMember


R = OrganizationMember.RoleChoices

router = Router(tags=["Dispatch"], auth=JWTAuthBearer())

DISPATCH_CREATORS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER]
DISPATCH_VIEWERS = [
    R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER,
    R.TRACKING_OFFICER, R.SALES,
]
STATUS_UPDATERS = [
    R.ORG_ADMIN, R.MANAGEMENT,
    R.LOGISTICS_OFFICER, R.TRACKING_OFFICER,
]
CANCELLERS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER]


# ── Dispatch endpoints ─────────────────────────────────────

@router.post("/{org_id}/create", response=BaseResponseSchema)
@require_roles(*DISPATCH_CREATORS)
def create_dispatch(request, org_id: UUID, data: DispatchCreateSchema) -> BaseResponseSchema:
    """
    Creates a new dispatch / TMR.
    Validates truck is not on an active trip before creating.
    """
    try:
        user_id = request.auth
        # user = request.auth.get("user_id")
        print(user_id)
        # print(user)
        dispatch = create_dispatch_service(data, org_id, user_id)
        return create_response(
            status_code=StatusCode.CREATED,
            data=dispatch
        )
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/dispatches", response=list[dict])
@require_roles(*DISPATCH_VIEWERS)
def list_dispatches(
    request,
    status: str | None = None,
    truck_id: UUID | None = None,
    customer_id: UUID | None = None,
) -> list[dict]:
    """
    Lists dispatches for the organization.
    Optional query params: ?status=in_transit, ?truck_id=..., ?customer_id=...
    """
    try:
        org_id = request.auth.get("org_id")
        results = list_dispatches_service(
            org_id, status, truck_id, customer_id
        )
        return create_response(
            status_code=StatusCode.OK,
            data=results
        )
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/{org_id}/dispatches/{dispatch_id}", response=dict)
@require_roles(*DISPATCH_VIEWERS)
def get_dispatch(request, org_id: UUID, dispatch_id: UUID) -> dict:
    """Retrieves a single dispatch with full related data."""
    try:
        # org_id = request.auth.get("org_id")
        dispatch = get_dispatch_service(dispatch_id, org_id)

        return create_response(
            data=dispatch,
            status_code=StatusCode.OK
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/{org_id}/dispatches/{dispatch_id}", response=dict)
@require_roles(*DISPATCH_CREATORS)
def update_dispatch(
    request, org_id: UUID, dispatch_id: UUID, data: DispatchUpdateSchema
) -> dict:
    """
    Updates a dispatch.
    Only permitted while status is PENDING or LOADING.
    """
    try:
        # org_id = request.auth.get("org_id")
        updated_dispatch = update_dispatch_service(dispatch_id, org_id, data)

        return create_response(
            data=updated_dispatch,
            status_code=StatusCode.OK
        )
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/{org_id}/dispatches/{dispatch_id}/status", response=BaseResponseSchema)
@require_roles(*STATUS_UPDATERS)
def update_dispatch_status(
    request, org_id: UUID, dispatch_id: UUID, data: DispatchStatusUpdateSchema
) -> BaseResponseSchema:
    """Manual dispatch status override with audit log entry."""
    try:
        # org_id = request.auth.get("org_id")
        user_id = request.auth
        dispatch = update_dispatch_status_service(
            dispatch_id, org_id, data, user_id
        )
        return create_response(
            data=dispatch,
            status_code=StatusCode.OK
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/dispatches/{dispatch_id}/cancel", response=dict)
@require_roles(*CANCELLERS)
def cancel_dispatch(
    request, dispatch_id: UUID, data: DispatchStatusUpdateSchema
) -> dict:
    """
    Cancels a dispatch.
    Only permitted while status is PENDING or LOADING.
    """
    try:
        org_id = request.auth.get("org_id")
        user_id = request.auth.get("user_id")
        dispatch = cancel_dispatch_service(
            dispatch_id, org_id, user_id, data.note
        )
        return create_response(
            data=dispatch,
            status_code=StatusCode.OK
        )
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# @router.get(
#     "/dispatches/{dispatch_id}/history",
#     response=list[dict],
# )
# @require_roles(*DISPATCH_VIEWERS)
# def get_dispatch_history(
#     request, dispatch_id: UUID
# ) -> list[dict]:
#     """Returns full status change history for a dispatch."""
#     try:
#         org_id = request.auth.get("org_id")
#         history = get_dispatch_status_history_service(dispatch_id, org_id)
#         return create_response(
#             data=history,
#             status_code=StatusCode.OK
#         )
#     except NotFoundException as e:
#         raise NotFoundException(str(e)) from e
#     except BadRequestException as e:
#         raise BadRequestException(str(e)) from e


# ── Driver arrival and OTP endpoints ───────────────────────

@router.patch("/{org_id}/dispatches/generate/arrival", response=BaseResponseSchema)
# @require_roles(R.DRIVER)
def driver_arrival(
    request,
    org_id: UUID,
    data: DriverArrivalSchema
) -> BaseResponseSchema:
    """
    Posted by driver when arriving at customer site.
    Generates OTP and updates status to ARRIVED.
    """
    try:
        # org_id = request.auth.get("org_id")
        dispatch = driver_arrival_service(data.dispatch_id, org_id)
        return create_response(
            data=dispatch,
            status_code=StatusCode.OK
        )
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


@router.post("/{org_id}/dispatches/resend-otp", response=dict)
@require_roles(R.DRIVER, R.TRACKING_OFFICER, R.LOGISTICS_OFFICER)
def resend_otp(
    request,
    org_id: UUID,
    data: ResendOTPSchema
) -> dict:
    """Regenerates and resends OTP to customer."""
    try:
        # org_id = request.auth.get("org_id")
        dispatch = resend_otp_service(data.dispatch_id, org_id)
        return create_response(
            data=dispatch,
            status_code=StatusCode.OK
        )
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


@router.post(
    "/{org_id}/dispatches/{dispatch_id}/confirm-delivery",
    response=BaseResponseSchema,
)
# @require_roles(R.CUSTOMER)
def confirm_delivery(
    request,
    org_id: UUID,
    dispatch_id: UUID,
    data: DeliveryConfirmationCreateSchema,
) -> dict:
    """
    Confirms delivery via OTP.
    Customer role only — submitted from the customer portal.
    Validates OTP, records waybridge weight, computes variance.
    """
    try:
        # org_id = request.auth.get("org_id")
        confirmation = confirm_delivery_service(dispatch_id, org_id, data)
        return create_response(
            data=confirmation,
            status_code=StatusCode.CREATED
        )
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


# ── Trip Metadata endpoints ────────────────────────────────

@router.post(
    "/dispatches/{dispatch_id}/trip-metadata",
    response=dict,
)
@require_roles(*DISPATCH_CREATORS)
def create_trip_metadata(
    request, dispatch_id: UUID, data: TripMetadataCreateSchema
) -> dict:
    """
    Creates trip metadata for a dispatch.
    Fails if metadata already exists — use PATCH to update.
    """
    try:
        org_id = request.auth.get("org_id")
        metadata = create_trip_metadata_service(dispatch_id, org_id, data)
        return create_response(
            data=metadata,
            status_code=StatusCode.CREATED
        )
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get(
    "/dispatches/{dispatch_id}/trip-metadata",
    response=dict,
)
@require_roles(*DISPATCH_VIEWERS)
def get_trip_metadata(
    request, dispatch_id: UUID
) -> dict:
    """Retrieves trip metadata for a dispatch."""
    try:
        org_id = request.auth.get("org_id")
        metadata = get_trip_metadata_service(dispatch_id, org_id)
        return create_response(
            data=metadata,
            status_code=StatusCode.OK
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch(
    "/dispatches/{dispatch_id}/trip-metadata",
    response=dict,
)
@require_roles(*DISPATCH_CREATORS)
def update_trip_metadata(
    request, dispatch_id: UUID, data: TripMetadataUpdateSchema
) -> dict:
    """Partially updates trip metadata."""
    try:
        org_id = request.auth.get("org_id")
        metadata = update_trip_metadata_service(dispatch_id, org_id, data)
        return create_response(
            data=metadata,
            status_code=StatusCode.OK
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
