# organization/views.py

from uuid import UUID
from ninja import Router
from access.auth import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException,
)
from config.permissions import require_roles
from config.validators import TenantService
from config.schema import StatusCode, create_response
from organization.schema import (
    OrganizationCreateSchema,
    OrganizationUpdateSchema,
    OrganizationOrgAdminUpdateSchema,
    OrganizationSettingsUpdateSchema,
)
from organization.services import (
    create_organization_service,
    list_organizations_service,
    get_organization_service,
    update_organization_service,
    org_admin_update_organization_service,
    deactivate_organization_service,
    get_org_settings_service,
    update_org_settings_service,
)
from users.models import Role

R = Role.RoleName


router = Router(tags=["Organizations"], auth=JWTAuthBearer())


@router.post("/organizations", auth=None)
async def create_organization(request, data: OrganizationCreateSchema) -> dict:
    """
    Creates a new organization.
    Superuser only — no JWT auth required here since
    this is called by the platform superuser directly.
    Only accessible via Django admin or a secured internal endpoint.
    """
    try:
        if not request.user.is_superuser:
            raise ForbiddenException(
                "Access denied: Only superusers can create organizations"
            ) from None
        result = await create_organization_service(data)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except Exception as e:
        raise BadRequestException(str(e)) from e


@router.get("/organizations")
async def list_organizations(request) -> dict:
    """
    Lists all organizations.
    Superuser only.
    """
    try:
        auth = request.auth
        if not auth.get("is_superuser"):
            raise ForbiddenException(
                "Access denied: Only superusers can list all organizations"
            ) from None
        result = await list_organizations_service()
        return create_response(status_code=StatusCode.OK, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organizations/{org_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
async def get_organization(request, org_id: UUID) -> dict:
    """
    Retrieves a single organization.
    Org admin can only retrieve their own org.
    Superuser can retrieve any.
    """
    try:
        auth = request.auth
        caller_org_id = auth.get("org_id")
        tenant_access = TenantService(request)

        has_access = tenant_access.check_tenant_id(caller_org_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        # # Org admin can only see their own org
        # if not auth.get("is_superuser"):
        #     if str(org_id) != str(caller_org_id):
        #         raise ForbiddenException(
        #             "You can only view your own organization"
        #         ) from None

        result = await get_organization_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organizations/{org_id}/admin-update")
@require_roles(R.ORG_ADMIN)
async def org_admin_update_organization(
    request, org_id: UUID, data: OrganizationOrgAdminUpdateSchema
) -> dict:
    """
    Restricted update for org admin.
    Can only change name and industry.
    Must be updating their own organization.
    """
    try:
        auth = request.auth
        caller_org_id = auth.get("org_id")
        tenant_access = TenantService(request)

        has_access = tenant_access.check_tenant_id(caller_org_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        # if str(org_id) != str(caller_org_id):
        #     raise ForbiddenException(
        #         "You can only update your own organization"
        #     ) from None

        result = await org_admin_update_organization_service(org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organizations/{org_id}")
async def update_organization(
    request, org_id: UUID, data: OrganizationUpdateSchema
) -> dict:
    """
    Full update — superuser only.
    """
    try:
        auth = request.auth
        if not auth.get("is_superuser"):
            raise ForbiddenException(
                "Access denied: Only superusers can perform full organization updates"
            ) from None

        result = await update_organization_service(org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organizations/{org_id}")
async def deactivate_organization(request, org_id: UUID) -> dict:
    """
    Deactivates an organization — superuser only.
    """
    try:
        auth = request.auth
        if not auth.get("is_superuser"):
            raise ForbiddenException(
                "Access denied: Only superusers can deactivate organizations"
            ) from None

        await deactivate_organization_service(org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Organization deactivated successfully.",
        )
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organizations/{org_id}/settings")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
async def get_org_settings(request, org_id: UUID) -> dict:
    """Retrieves settings for an organization."""
    try:
        auth = request.auth
        # if str(org_id) != str(auth.get("org_id")):
        #     raise ForbiddenException(
        #         "You can only view your own organization settings"
        #     ) from None
        tenant_access = TenantService(request)

        has_access = tenant_access.check_tenant_id(org_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await get_org_settings_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organizations/{org_id}/settings")
@require_roles(R.ORG_ADMIN)
async def update_org_settings(
    request, org_id: UUID, data: OrganizationSettingsUpdateSchema
) -> dict:
    """Updates organization settings — org admin only."""
    try:
        auth = request.auth
        # if str(org_id) != str(auth.get("org_id")):
        #     raise ForbiddenException(
        #         "You can only update your own organization settings"
        #     ) from None
        tenant_access = TenantService(request)

        has_access = tenant_access.check_tenant_id(org_id)

        if has_access is None:
            return create_response(
                status_code=StatusCode.FORBIDDEN,
                data=None,
                message="Access denied. You do not own this resource"
            )

        result = await update_org_settings_service(org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except ForbiddenException as e:
        raise ForbiddenException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
