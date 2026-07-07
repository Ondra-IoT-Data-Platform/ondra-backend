from uuid import UUID
from ninja import Router
from access.auth import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response
from users.models import Role
from users.schema import (
    UserCreateSchema,
    UserUpdateSchema,
    UserRoleUpdateSchema,
    OfficeProfileCreateSchema,
    OfficeProfileUpdateSchema,
    DriverProfileCreateSchema,
    DriverProfileUpdateSchema,
)
from users.services import (
    create_user_service,
    list_users_service,
    get_user_service,
    update_user_service,
    update_user_role_service,
    deactivate_user_service,
    create_office_profile_service,
    update_office_profile_service,
    get_office_profile_service,
    create_driver_profile_service,
    update_driver_profile_service,
    get_driver_profile_service,
)

R = Role.RoleName
router = Router(tags=["Users"], auth=JWTAuthBearer())

USER_MANAGERS = [R.ORG_ADMIN, R.MANAGEMENT]


# ── User endpoints ─────────────────────────────────────────

@router.post("/users")
@require_roles(*USER_MANAGERS)
async def create_user(request, data: UserCreateSchema) -> dict:
    """
    Creates a new user within the authenticated user's organization.
    Organization is always inferred from token — never from client input.
    """
    try:
        org_id = request.auth.get("org_id")
        result = await create_user_service(data, org_id)
        return create_response(
            status_code=StatusCode.CREATED,
            data=result,
        )
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/users")
@require_roles(*USER_MANAGERS)
async def list_users(request) -> dict:
    """Lists all users in the authenticated user's organization."""
    try:
        org_id = request.auth.get("org_id")
        result = await list_users_service(org_id)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/users/{user_id}")
@require_roles(*USER_MANAGERS)
async def get_user(request, user_id: UUID) -> dict:
    """
    Retrieves a single user with their office or driver profile.
    Scoped to the authenticated user's organization.
    """
    try:
        org_id = request.auth.get("org_id")
        result = await get_user_service(user_id, org_id)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/users/{user_id}")
@require_roles(*USER_MANAGERS)
async def update_user(request, user_id: UUID, data: UserUpdateSchema) -> dict:
    """Updates a user's email or active status."""
    try:
        org_id = request.auth.get("org_id")
        result = await update_user_service(user_id, org_id, data)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/users/{user_id}/role")
@require_roles(R.ORG_ADMIN)
async def update_user_role(
    request, user_id: UUID, data: UserRoleUpdateSchema
) -> dict:
    """
    Changes a user's role.
    Org admin only — management cannot reassign roles.
    Role must belong to the same organization.
    """
    try:
        org_id = request.auth.get("org_id")
        result = await update_user_role_service(user_id, org_id, data)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/users/{user_id}")
@require_roles(R.ORG_ADMIN)
async def deactivate_user(request, user_id: UUID) -> dict:
    """
    Soft deletes a user by setting is_active to False.
    Org admin only.
    """
    try:
        org_id = request.auth.get("org_id")
        await deactivate_user_service(user_id, org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="User deactivated successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Office profile endpoints ───────────────────────────────

@router.post("/users/{user_id}/office-profile")
@require_roles(*USER_MANAGERS)
async def create_office_profile(
    request, user_id: UUID, data: OfficeProfileCreateSchema
) -> dict:
    """
    Creates an office profile for a user.
    Used for all non-driver roles.
    Fails if profile already exists — use PATCH to update.
    """
    try:
        org_id = request.auth.get("org_id")
        result = await create_office_profile_service(user_id, org_id, data)
        return create_response(
            status_code=StatusCode.CREATED,
            data=result,
        )
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/users/{user_id}/office-profile")
@require_roles(*USER_MANAGERS)
async def get_office_profile(request, user_id: UUID) -> dict:
    """Retrieves the office profile for a user."""
    try:
        org_id = request.auth.get("org_id")
        result = await get_office_profile_service(user_id, org_id)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/users/{user_id}/office-profile")
@require_roles(*USER_MANAGERS)
async def update_office_profile(
    request, user_id: UUID, data: OfficeProfileUpdateSchema
) -> dict:
    """Updates an existing office profile."""
    try:
        org_id = request.auth.get("org_id")
        result = await update_office_profile_service(user_id, org_id, data)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Driver profile endpoints ───────────────────────────────

@router.post("/users/{user_id}/driver-profile")
@require_roles(*USER_MANAGERS)
async def create_driver_profile(
    request, user_id: UUID, data: DriverProfileCreateSchema
) -> dict:
    """
    Creates a driver profile for a user.
    Used specifically for users with the Driver role.
    Fails if profile already exists — use PATCH to update.
    """
    try:
        org_id = request.auth.get("org_id")
        result = await create_driver_profile_service(user_id, org_id, data)
        return create_response(
            status_code=StatusCode.CREATED,
            data=result,
        )
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/users/{user_id}/driver-profile")
@require_roles(*USER_MANAGERS)
async def get_driver_profile(request, user_id: UUID) -> dict:
    """Retrieves the driver profile for a user."""
    try:
        org_id = request.auth.get("org_id")
        result = await get_driver_profile_service(user_id, org_id)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/users/{user_id}/driver-profile")
@require_roles(*USER_MANAGERS)
async def update_driver_profile(
    request, user_id: UUID, data: DriverProfileUpdateSchema
) -> dict:
    """Updates an existing driver profile."""
    try:
        org_id = request.auth.get("org_id")
        result = await update_driver_profile_service(user_id, org_id, data)
        return create_response(
            status_code=StatusCode.OK,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
