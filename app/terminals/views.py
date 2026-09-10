from uuid import UUID
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
from access.auth_utils import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response
from config.validators import TenantService
from organization.models import OrganizationMember



R = OrganizationMember.RoleChoices

router = Router(tags=["Terminals & Gates"], auth=JWTAuthBearer())


TERMINAL_MANAGERS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER]
TERMINAL_VIEWERS = [
    R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER,
    R.TRACKING_OFFICER, R.WORKSHOP, R.SALES
]


@router.post("/organization/{org_id}/terminals", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
def create_terminal(request, org_id: UUID, data: TerminalCreateSchema) -> dict:

    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        result = create_terminal_service(org_id, data)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/terminals", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
def list_terminals(request, org_id: UUID) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )
        result = list_terminals_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/terminals/{terminal_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
def get_terminal(request, org_id: UUID, terminal_id: int) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)


        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )
        result = get_terminal_service(request.auth, org_id, terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/terminals/{terminal_id}/with-gates", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
def get_terminal_with_gates(request, org_id: UUID, terminal_id: int) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        result = get_terminal_with_gates_service(org_id, terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/terminals/{terminal_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
def update_terminal(
    request, org_id: UUID, terminal_id: int, data: TerminalUpdateSchema
) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        result = update_terminal_service(org_id, terminal_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organization/{org_id}/terminals/{terminal_id}", auth=JWTAuthBearer())
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def delete_terminal(request, org_id: UUID, terminal_id: int) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        delete_terminal_service(org_id, terminal_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Terminal deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.post("/organization/{org_id}/gates", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
def create_gate(request, org_id: UUID, data: GateCreateSchema) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        result = create_gate_service(org_id, data)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/terminals/{terminal_id}/gates", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
def list_gates(request, org_id: UUID, terminal_id: int) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )
        result = list_gates_service(org_id, terminal_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/gates/{gate_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_VIEWERS)
def get_gate(request, org_id: UUID, gate_id: int) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        result = get_gate_service(org_id, gate_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/gates/{gate_id}", auth=JWTAuthBearer())
@require_roles(*TERMINAL_MANAGERS)
def update_gate(request, org_id: UUID, gate_id: int, data: GateUpdateSchema) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        result = update_gate_service(org_id, gate_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organization/{org_id}/gates/{gate_id}", auth=JWTAuthBearer())
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def delete_gate(request, org_id: UUID, gate_id: int) -> dict:
    try:
        # tenant_access = TenantService(request)
        # has_access = tenant_access.check_tenant_id(org_id)

        # if has_access is None:
        #     return create_response(
        #         status_code=StatusCode.FORBIDDEN,
        #         data=None,
        #         message="Access denied. You do not own this resource"
        #     )

        delete_gate_service(org_id, gate_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Gate deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
