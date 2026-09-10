from uuid import UUID

from ninja import Router
from django.db import transaction
from access.auth_utils import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response
from fleet.schema import (
    ProductCreateSchema,
    ProductUpdateSchema,
    RouteCreateSchema,
    RouteUpdateSchema,
    TruckCreateSchema,
    TruckStatusUpdateSchema,
    TruckUpdateSchema,
)
from fleet.services import (
    create_product_service,
    create_route_service,
    create_truck_service,
    deactivate_truck_service,
    get_product_service,
    get_route_service,
    get_truck_service,
    get_truck_status_history_service,
    list_products_service,
    list_routes_service,
    list_trucks_service,
    update_product_service,
    update_route_service,
    update_truck_service,
    update_truck_status_service,
    delete_route_service
)
from organization.models import OrganizationMember


R = OrganizationMember.RoleChoices


router = Router(tags=["Fleet"], auth=JWTAuthBearer())

FLEET_MANAGERS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER]
FLEET_VIEWERS = [
    R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER,
    R.TRACKING_OFFICER, R.WORKSHOP, R.SALES,
]
STATUS_UPDATERS = [
    R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER,
    R.TRACKING_OFFICER, R.WORKSHOP,
]


# ── Products ───────────────────────────────────────────────

@router.post("/organization/{org_id}/products")
@require_roles(*FLEET_MANAGERS)
@transaction.atomic
def create_product(request, org_id: UUID, data: ProductCreateSchema) -> dict:
    """Creates a product — Management, Logistics Officer, Org Admin only."""
    try:
        result = create_product_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/products")
@require_roles(*FLEET_VIEWERS)
def list_products(request, org_id: UUID) -> dict:
    """Lists all products for the organization."""
    try:
        result = list_products_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/products/{product_id}")
@require_roles(*FLEET_VIEWERS)
def get_product(request, org_id: UUID, product_id: UUID) -> dict:
    """Retrieves a single product."""
    try:
        result = get_product_service(product_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/products/{product_id}")
@require_roles(*FLEET_MANAGERS)
def update_product(
    request, org_id: UUID, product_id: UUID, data: ProductUpdateSchema
) -> dict:
    """Updates a product."""
    try:
        result = update_product_service(product_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Routes ─────────────────────────────────────────────────

@router.post("/organization/{org_id}/routes")
@require_roles(*FLEET_MANAGERS)
@transaction.atomic
def create_route(request, org_id: UUID, data: RouteCreateSchema) -> dict:
    """Creates a route."""
    try:
        result = create_route_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/routes")
@require_roles(*FLEET_VIEWERS)
def list_routes(request, org_id: UUID) -> dict:
    """Lists all routes for the organization."""
    try:
        result = list_routes_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/routes/{route_id}")
@require_roles(*FLEET_VIEWERS)
def get_route(request, org_id: UUID, route_id: UUID) -> dict:
    """Retrieves a single route."""
    try:
        result = get_route_service(route_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/routes/{route_id}")
@require_roles(*FLEET_MANAGERS)
def update_route(
    request, org_id: UUID, route_id: UUID, data: RouteUpdateSchema
) -> dict:
    """Updates a route."""
    try:
        result = update_route_service(route_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organization/{org_id}/routes/{route_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def delete_route(request, org_id: UUID, route_id: UUID) -> dict:
    """Deletes a route — Management and Org Admin only."""
    try:
        delete_route_service(route_id, org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Route deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Trucks ─────────────────────────────────────────────────

@router.post("/organization/{org_id}/trucks")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER)
@transaction.atomic
def create_truck(request, org_id: UUID, data: TruckCreateSchema) -> dict:
    """Registers a new truck."""
    try:
        result = create_truck_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/trucks")
@require_roles(*FLEET_VIEWERS)
def list_trucks(
    request,
    org_id: UUID,
    status: str | None = None
) -> dict:
    """
    Lists all trucks for the organization.
    Optionally filter by status via query param e.g. ?status=outbound
    """
    try:
        result = list_trucks_service(org_id, status)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/trucks/{truck_id}")
@require_roles(*FLEET_VIEWERS)
def get_truck(request, org_id: UUID, truck_id: UUID) -> dict:
    """Retrieves a single truck with current location."""
    try:
        result = get_truck_service(truck_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/trucks/{truck_id}")
@require_roles(*FLEET_MANAGERS)
def update_truck(
    request, org_id: UUID, truck_id: UUID, data: TruckUpdateSchema
) -> dict:
    """Updates truck details."""
    try:
        result = update_truck_service(truck_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/trucks/{truck_id}/status")
@require_roles(*STATUS_UPDATERS)
def update_truck_status(
    request, org_id: UUID, truck_id: UUID, data: TruckStatusUpdateSchema
) -> dict:
    """
    Manually overrides a truck status.
    Writes an audit log entry with trigger source set to MANUAL.
    RFID-triggered status changes go through the terminals app — not here.
    """
    try:

        user_id = request.auth.get("user_id")
        result = update_truck_status_service(
            truck_id, org_id, data, user_id
        )
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/trucks/{truck_id}/history")
@require_roles(*FLEET_VIEWERS)
def get_truck_status_history(request, org_id: UUID, truck_id: UUID) -> dict:
    """Returns the full status change history for a truck."""
    try:
        result = get_truck_status_history_service(truck_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organization/{org_id}/trucks/{truck_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def deactivate_truck(request, org_id: UUID, truck_id: UUID) -> dict:
    """
    Decommissions a truck — sets is_active False and status to DECOMMISSIONED.
    Management and Org Admin only.
    """
    try:
        deactivate_truck_service(truck_id, org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Truck decommissioned successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
