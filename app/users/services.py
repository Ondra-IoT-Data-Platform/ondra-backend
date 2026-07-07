from uuid import UUID
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from config.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from users.models import Role, OfficeProfile, DriverProfile
from users.schema import (
    UserCreateSchema,
    UserUpdateSchema,
    UserRoleUpdateSchema,
    UserOutSchema,
    UserWithProfileOutSchema,
    OfficeProfileCreateSchema,
    OfficeProfileUpdateSchema,
    OfficeProfileOutSchema,
    DriverProfileCreateSchema,
    DriverProfileUpdateSchema,
    DriverProfileOutSchema,
)

User = get_user_model()


# ── User services ──────────────────────────────────────────

async def create_user_service(
    data: UserCreateSchema,
    organization_id: UUID,
) -> UserOutSchema:
    """
    Creates a new user.
    organization_id comes from the authenticated user's token —
    never from client input.
    """
    try:
        exists = await User.objects.filter(
            email=data.email
        ).aexists()
        if exists:
            raise ConflictException(
                f"A user with email '{data.email}' already exists"
            ) from None

        role = await Role.objects.aget(
            id=data.role_id,
            organization_id=organization_id,
        )

        user = await User.objects.acreate(
            email=data.email,
            password=make_password(data.password),
            organization_id=organization_id,
            role=role,
        )

        # Reload with select_related so schema resolver
        # can access user.role.name without extra query
        user = await (
            User.objects
            .select_related("role", "organization")
            .aget(id=user.id)
        )

        return UserOutSchema.from_orm(user)

    except Role.DoesNotExist:
        raise NotFoundException(
            "Role not found in this organization"
        ) from None
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def list_users_service(
    organization_id: UUID,
) -> list[UserOutSchema]:
    """
    Lists all users in an organization.
    Always scoped to the authenticated user's organization.
    """
    try:
        users = (
            User.objects
            .filter(organization_id=organization_id)
            .select_related("role", "organization")
            .order_by("created_at")
        )
        return [
            UserOutSchema.from_orm(user)
            async for user in users
        ]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_user_service(
    user_id: UUID,
    organization_id: UUID,
) -> UserWithProfileOutSchema:
    """
    Retrieves a single user with their profile.
    Scoped to organization.
    """
    try:
        user = await (
            User.objects
            .select_related("role", "organization")
            .aget(id=user_id, organization_id=organization_id)
        )

        office_profile = None
        driver_profile = None

        try:
            profile = await OfficeProfile.objects.aget(user=user)
            office_profile = OfficeProfileOutSchema.from_orm(profile)
        except OfficeProfile.DoesNotExist:
            pass

        try:
            profile = await DriverProfile.objects.aget(user=user)
            driver_profile = DriverProfileOutSchema.from_orm(profile)
        except DriverProfile.DoesNotExist:
            pass

        return UserWithProfileOutSchema(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            organization_id=user.organization_id,
            role_name=user.role.name if user.role else None,
            created_at=user.created_at,
            updated_at=user.updated_at,
            office_profile=office_profile,
            driver_profile=driver_profile,
        )

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_user_service(
    user_id: UUID,
    organization_id: UUID,
    data: UserUpdateSchema,
) -> UserOutSchema:
    """
    Updates a user's email or active status.
    Scoped to organization.
    """
    try:
        user = await (
            User.objects
            .select_related("role", "organization")
            .aget(id=user_id, organization_id=organization_id)
        )

        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        await user.asave()

        # Reload after save to get fresh state
        user = await (
            User.objects
            .select_related("role", "organization")
            .aget(id=user.id)
        )
        return UserOutSchema.from_orm(user)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_user_role_service(
    user_id: UUID,
    organization_id: UUID,
    data: UserRoleUpdateSchema,
) -> UserOutSchema:
    """
    Changes a user's role.
    Role must belong to the same organization.
    Org admin only.
    """
    try:
        user = await (
            User.objects
            .select_related("role", "organization")
            .aget(id=user_id, organization_id=organization_id)
        )

        role = await Role.objects.aget(
            id=data.role_id,
            organization_id=organization_id,
        )

        user.role = role
        await user.asave()

        user = await (
            User.objects
            .select_related("role", "organization")
            .aget(id=user.id)
        )
        return UserOutSchema.from_orm(user)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except Role.DoesNotExist:
        raise NotFoundException(
            "Role not found in this organization"
        ) from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def deactivate_user_service(
    user_id: UUID,
    organization_id: UUID,
) -> None:
    """
    Soft deletes a user by marking them inactive.
    Scoped to organization.
    """
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )
        user.is_active = False
        await user.asave()

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Office profile services ────────────────────────────────

async def create_office_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: OfficeProfileCreateSchema,
) -> OfficeProfileOutSchema:
    """
    Creates an office profile for a user.
    User must belong to the caller's organization.
    """
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )

        exists = await OfficeProfile.objects.filter(
            user=user
        ).aexists()
        if exists:
            raise ConflictException(
                "Office profile already exists for this user"
            ) from None

        profile = await OfficeProfile.objects.acreate(
            user=user,
            **data.dict(exclude_unset=True),
        )
        return OfficeProfileOutSchema.from_orm(profile)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_office_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: OfficeProfileUpdateSchema,
) -> OfficeProfileOutSchema:
    """
    Updates an existing office profile.
    User must belong to the caller's organization.
    """
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )

        profile = await OfficeProfile.objects.aget(user=user)

        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        await profile.asave()

        return OfficeProfileOutSchema.from_orm(profile)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except OfficeProfile.DoesNotExist:
        raise NotFoundException("Office profile not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_office_profile_service(
    user_id: UUID,
    organization_id: UUID,
) -> OfficeProfileOutSchema:
    """Retrieves the office profile for a user."""
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )
        profile = await OfficeProfile.objects.aget(user=user)
        return OfficeProfileOutSchema.from_orm(profile)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except OfficeProfile.DoesNotExist:
        raise NotFoundException("Office profile not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Driver profile services ────────────────────────────────

async def create_driver_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: DriverProfileCreateSchema,
) -> DriverProfileOutSchema:
    """
    Creates a driver profile for a user.
    User must belong to the caller's organization.
    A user should only have one driver profile.
    """
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )

        exists = await DriverProfile.objects.filter(
            user=user
        ).aexists()
        if exists:
            raise ConflictException(
                "Driver profile already exists for this user"
            ) from None

        profile = await DriverProfile.objects.acreate(
            user=user,
            **data.dict(exclude_unset=True),
        )
        return DriverProfileOutSchema.from_orm(profile)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_driver_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: DriverProfileUpdateSchema,
) -> DriverProfileOutSchema:
    """
    Updates an existing driver profile.
    User must belong to the caller's organization.
    """
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )

        profile = await DriverProfile.objects.aget(user=user)

        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        await profile.asave()

        return DriverProfileOutSchema.from_orm(profile)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except DriverProfile.DoesNotExist:
        raise NotFoundException("Driver profile not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_driver_profile_service(
    user_id: UUID,
    organization_id: UUID,
) -> DriverProfileOutSchema:
    """Retrieves the driver profile for a user."""
    try:
        user = await User.objects.aget(
            id=user_id,
            organization_id=organization_id,
        )
        profile = await DriverProfile.objects.aget(user=user)
        return DriverProfileOutSchema.from_orm(profile)

    except User.DoesNotExist:
        raise NotFoundException("User not found") from None
    except DriverProfile.DoesNotExist:
        raise NotFoundException("Driver profile not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e
