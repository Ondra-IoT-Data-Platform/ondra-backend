from uuid import UUID

from ninja import Router

from access.auth import JWTAuthBearer
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
from users.models import Role

R = Role.RoleName
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

@router.post("/products")
@require_roles(*FLEET_MANAGERS)
async def create_product(request, data: ProductCreateSchema) -> dict:
    """Creates a product — Management, Logistics Officer, Org Admin only."""
    try:
        org_id = request.auth.get("org_id")
        result = await create_product_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/products")
@require_roles(*FLEET_VIEWERS)
async def list_products(request) -> dict:
    """Lists all products for the organization."""
    try:
        org_id = request.auth.get("org_id")
        result = await list_products_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/products/{product_id}")
@require_roles(*FLEET_VIEWERS)
async def get_product(request, product_id: UUID) -> dict:
    """Retrieves a single product."""
    try:
        org_id = request.auth.get("org_id")
        result = await get_product_service(product_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/products/{product_id}")
@require_roles(*FLEET_MANAGERS)
async def update_product(
    request, product_id: UUID, data: ProductUpdateSchema
) -> dict:
    """Updates a product."""
    try:
        org_id = request.auth.get("org_id")
        result = await update_product_service(product_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Routes ─────────────────────────────────────────────────

@router.post("/routes")
@require_roles(*FLEET_MANAGERS)
async def create_route(request, data: RouteCreateSchema) -> dict:
    """Creates a route."""
    try:
        org_id = request.auth.get("org_id")
        result = await create_route_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/routes")
@require_roles(*FLEET_VIEWERS)
async def list_routes(request) -> dict:
    """Lists all routes for the organization."""
    try:
        org_id = request.auth.get("org_id")
        result = await list_routes_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/routes/{route_id}")
@require_roles(*FLEET_VIEWERS)
async def get_route(request, route_id: UUID) -> dict:
    """Retrieves a single route."""
    try:
        org_id = request.auth.get("org_id")
        result = await get_route_service(route_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/routes/{route_id}")
@require_roles(*FLEET_MANAGERS)
async def update_route(
    request, route_id: UUID, data: RouteUpdateSchema
) -> dict:
    """Updates a route."""
    try:
        org_id = request.auth.get("org_id")
        result = await update_route_service(route_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/routes/{route_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
async def delete_route(request, route_id: UUID) -> dict:
    """Deletes a route — Management and Org Admin only."""
    try:
        org_id = request.auth.get("org_id")
        await delete_route_service(route_id, org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Route deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Trucks ─────────────────────────────────────────────────

@router.post("/trucks")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER)
async def create_truck(request, data: TruckCreateSchema) -> dict:
    """Registers a new truck."""
    try:
        org_id = request.auth.get("org_id")
        result = await create_truck_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/trucks")
@require_roles(*FLEET_VIEWERS)
async def list_trucks(
    request, status: str | None = None
) -> dict:
    """
    Lists all trucks for the organization.
    Optionally filter by status via query param e.g. ?status=outbound
    """
    try:
        org_id = request.auth.get("org_id")
        result = await list_trucks_service(org_id, status)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/trucks/{truck_id}")
@require_roles(*FLEET_VIEWERS)
async def get_truck(request, truck_id: UUID) -> dict:
    """Retrieves a single truck with current location."""
    try:
        org_id = request.auth.get("org_id")
        result = await get_truck_service(truck_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/trucks/{truck_id}")
@require_roles(*FLEET_MANAGERS)
async def update_truck(
    request, truck_id: UUID, data: TruckUpdateSchema
) -> dict:
    """Updates truck details."""
    try:
        org_id = request.auth.get("org_id")
        result = await update_truck_service(truck_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/trucks/{truck_id}/status")
@require_roles(*STATUS_UPDATERS)
async def update_truck_status(
    request, truck_id: UUID, data: TruckStatusUpdateSchema
) -> dict:
    """
    Manually overrides a truck status.
    Writes an audit log entry with trigger source set to MANUAL.
    RFID-triggered status changes go through the terminals app — not here.
    """
    try:
        org_id = request.auth.get("org_id")
        user_id = request.auth.get("user_id")
        result = await update_truck_status_service(
            truck_id, org_id, data, user_id
        )
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/trucks/{truck_id}/history")
@require_roles(*FLEET_VIEWERS)
async def get_truck_status_history(request, truck_id: UUID) -> dict:
    """Returns the full status change history for a truck."""
    try:
        org_id = request.auth.get("org_id")
        result = await get_truck_status_history_service(truck_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/trucks/{truck_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
async def deactivate_truck(request, truck_id: UUID) -> dict:
    """
    Decommissions a truck — sets is_active False and status to DECOMMISSIONED.
    Management and Org Admin only.
    """
    try:
        org_id = request.auth.get("org_id")
        await deactivate_truck_service(truck_id, org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Truck decommissioned successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
