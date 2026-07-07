# app/terminals/views.py

from ninja import Router

from terminals.schema import (
    GateCreateSchema,
    GateUpdateSchema,
    TerminalCreateSchema,
    TerminalUpdateSchema,
)
from terminals.services import (
    create_gate_service,
    create_terminal_service,
    delete_gate_service,
    delete_terminal_service,
    get_gate_service,
    get_terminal_service,
    get_terminal_with_gates_service,
    list_gates_service,
    list_terminals_service,
    update_gate_service,
    update_terminal_service,
)
from access.auth import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response
from config.validators import TenantService
from users.models import Role


router = Router(tags=["Terminals & Gates"], auth=JWTAuthBearer())


R = Role.RoleName

TERMINAL_MANAGERS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER]
TERMINAL_VIEWERS = [
    R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER,
    R.TRACKING_OFFICER, R.WORKSHOP, R.SALES
]


@router.post("/terminals", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
async def create_terminal(request, data: TerminalCreateSchema) -> dict:

    try:
        organization_id =  request.auth.get("org_id")
        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await create_terminal_service(data)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/terminals", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
async def list_terminals(request) -> dict:
    try:
        organization_id =  request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )
        result = await list_terminals_service(organization_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/terminals/{terminal_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
async def get_terminal(request, terminal_id: int) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )
        result = await get_terminal_service(request.auth,  terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/terminals/{terminal_id}/with-gates", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
async def get_terminal_with_gates(request, terminal_id: int) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await get_terminal_with_gates_service(terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/terminals/{terminal_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
async def update_terminal(
    request, terminal_id: int, data: TerminalUpdateSchema
) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await update_terminal_service(terminal_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/terminals/{terminal_id}", auth=JWTAuthBearer())
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
async def delete_terminal(request, terminal_id: int) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        await delete_terminal_service(terminal_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Terminal deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.post("/gates", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
async def create_gate(request, data: GateCreateSchema) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await create_gate_service(data)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/terminals/{terminal_id}/gates", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
async def list_gates(request, terminal_id: int) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )
        result = await list_gates_service(terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/gates/{gate_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
async def get_gate(request, gate_id: int) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await get_gate_service(gate_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/gates/{gate_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
async def update_gate(request, gate_id: int, data: GateUpdateSchema) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await update_gate_service(gate_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/gates/{gate_id}", auth=JWTAuthBearer())
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
async def delete_gate(request, gate_id: int) -> dict:
    try:
        organization_id = request.auth.get("org_id")

        tenant_access = TenantService(request)
        has_access = tenant_access.check_tenant_id(organization_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        await delete_gate_service(gate_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Gate deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
