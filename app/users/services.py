# users/services.py
from uuid import UUID
from django.utils import timezone
from django.db import transaction

from config.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from users.models import User,  OfficeProfile, DriverProfile
from users.schema import (
    UserCreateSchema,
    UserUpdateSchema,
    UserOutSchema,
    UserWithProfileOutSchema,
    OfficeProfileCreateSchema,
    OfficeProfileUpdateSchema,
    OfficeProfileOutSchema,
    DriverProfileCreateSchema,
    DriverProfileUpdateSchema,
    DriverProfileOutSchema,
)
from access.models import TokenTypeChoices
from access.auth_utils import OTokenManager
from organization.models import Organizations



# ── User services ──────────────────────────────────────────

def create_user_service(
    data: UserCreateSchema,
) -> UserOutSchema:
    """
    Creates a new user using an organization onboarding token.
    The token proves the user is authorized to join the organization.
    """
    try:
        # Validate the organization token FIRST
        token_obj = OTokenManager.verify_otoken(
            data.organization_token,
            TokenTypeChoices.USER_ONBOARDING
        )

        if not token_obj:
            raise NotFoundException(
                "Invalid or expired organization onboarding token"
            )

        # Get the organization from the token
        organization = token_obj.organization
        if not organization:
            raise BadRequestException("Token is not associated with an organization")

        # Check if user already exists
        existing_user = User.objects.filter(email=data.email).first()

        if existing_user:
            # User exists - check if they're already a member
            if organization.members.filter(user=existing_user, is_active=True).exists():
                raise ConflictException(
                    f"User with email '{data.email}' is already a member of this organization"
                )

            # Use existing user
            user = existing_user
            is_new_user = False
        else:
            # Create new user
            user = User.objects.create_user(
                email=data.email,
                password=data.password
            )
            is_new_user = True

        # Get metadata from token
        metadata = token_obj.metadata or {}
        role = metadata.get('role', 'org_admin')

        # Add user to organization (if not already a member)
        with transaction.atomic():
            # Check again if user is already a member (for existing users)
            if not organization.members.filter(user=user, is_active=True).exists():
                organization.members.create(
                    user=user,
                    role=role,
                    joined_at=timezone.now()
                )

            # Mark the token as used
            OTokenManager.mark_used(token_obj)

            # Associate token with user
            token_obj.user = user
            token_obj.save(update_fields=['user'])

        # Return user response
        return UserOutSchema(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            organization_id=organization.id,
            role=role,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    except ConflictException:
        raise
    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create user: {str(e)}")




def create_user_from_invitation_service(
    data: UserCreateSchema,
) -> UserOutSchema:
    """
    Creates a new user from an invitation token.
    The user is added to the organization with the role specified in the token.
    """
    try:
        # Check if user already exists
        if User.objects.filter(email=data.email).exists():
            raise ConflictException(
                f"A user with email '{data.email}' already exists"
            )

        # Validate the invitation token
        token_obj = OTokenManager.verify_otoken(
            data.organization_token,
            TokenTypeChoices.USER_ONBOARDING
        )

        if not token_obj:
            raise NotFoundException(
                "Invalid or expired invitation token"
            )

        # Get the organization from the token
        organization = token_obj.organization
        if not organization:
            raise BadRequestException("Token is not associated with an organization")

        # Get role from token metadata
        # metadata = token_obj.metadata or {}
        # role = metadata.get('role', 'org_admin')

        # Create the user with transaction
        with transaction.atomic():
            # Create user
            user = User.objects.create_user(
                email=data.email,
                password=data.password
            )

            # Add user to organization
            organization.members.create(
                user=user,
                role=data.role,
                joined_at=timezone.now()
            )

            # Mark the token as used
            OTokenManager.mark_used(token_obj)

            # Associate token with user
            token_obj.user = user
            token_obj.save(update_fields=['user'])

        # Return user response
        return UserOutSchema(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            organization_id=organization.id,
            role=data.role,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    except ConflictException:
        raise
    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create user from invitation: {str(e)}")


def list_users_service(
    organization_id: UUID,
) -> list[UserOutSchema]:
    """
    Lists all users in an organization.
    Always scoped to the authenticated user's organization.
    """
    try:
        # Validate organization exists
        try:
            organization = Organizations.objects.get(id=organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        users = (
            User.objects
            .filter(
                organization_memberships__organization_id=organization_id,
                organization_memberships__is_active=True,
                is_active=True
            )
            .select_related('organization_memberships')
            .order_by("created_at")
            .distinct()
        )

        return [
            UserOutSchema(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                organization_id=organization_id,
                role=user.organization_memberships.filter(
                    organization_id=organization_id
                ).first().role if user.organization_memberships.filter(
                    organization_id=organization_id
                ).exists() else None,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to list users: {str(e)}")


def get_user_service(
    user_id: UUID,
    organization_id: UUID,
) -> UserWithProfileOutSchema:
    """
    Retrieves a single user with their profile.
    Scoped to organization.
    """
    try:
        # Validate organization exists
        try:
            organization = Organizations.objects.get(id=organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        # Get user with organization membership
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True,
            is_active=True
        ).select_related('organization_memberships').first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Get the member role
        member = user.organization_memberships.filter(
            organization_id=organization_id
        ).first()

        office_profile = None
        driver_profile = None

        try:
            profile = OfficeProfile.objects.get(user=user)
            office_profile = OfficeProfileOutSchema.from_orm(profile)
        except OfficeProfile.DoesNotExist:
            pass

        try:
            profile = DriverProfile.objects.get(user=user)
            driver_profile = DriverProfileOutSchema.from_orm(profile)
        except DriverProfile.DoesNotExist:
            pass

        return UserWithProfileOutSchema(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            is_active=user.is_active,
            organization_id=organization_id,
            role=member.role if member else None,
            created_at=user.created_at,
            updated_at=user.updated_at,
            office_profile=office_profile,
            driver_profile=driver_profile,
        )

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to get user: {str(e)}")


def update_user_service(
    user_id: UUID,
    organization_id: UUID,
    data: UserUpdateSchema,
) -> UserOutSchema:
    """
    Updates a user's details.
    Scoped to organization.
    """
    try:
        # Validate organization exists
        try:
            organization = Organizations.objects.get(id=organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        # Get user
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Update user fields
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field != 'password' and hasattr(user, field):
                setattr(user, field, value)

        if 'password' in update_data and update_data['password']:
            user.set_password(update_data['password'])

        user.save()

        # Get the member role
        member = user.organization_memberships.filter(
            organization_id=organization_id
        ).first()

        return UserOutSchema(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            is_active=user.is_active,
            organization_id=organization_id,
            role=member.role if member else None,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to update user: {str(e)}")


# def update_user_role_service(
#     user_id: UUID,
#     organization_id: UUID,
#     data: UserRoleUpdateSchema,
# ) -> UserOutSchema:
#     """
#     Changes a user's role.
#     Role must belong to the same organization.
#     Org admin only.
#     """
#     try:
#         # Validate organization exists
#         try:
#             organization = Organizations.objects.get(id=organization_id, is_active=True)
#         except Organizations.DoesNotExist:
#             raise NotFoundException("Organization not found")

#         # Get user
#         user = User.objects.filter(
#             id=user_id,
#             organization_memberships__organization_id=organization_id,
#             organization_memberships__is_active=True
#         ).first()

#         if not user:
#             raise NotFoundException("User not found in this organization")

#         # Get the member
#         member = user.organization_memberships.filter(
#             organization_id=organization_id
#         ).first()

#         if not member:
#             raise NotFoundException("User is not a member of this organization")

#         # Update role
#         member.role = data.role
#         member.save(update_fields=['role'])

#         return UserOutSchema(
#             id=user.id,
#             email=user.email,
#             first_name=user.first_name,
#             last_name=user.last_name,
#             phone=user.phone,
#             is_active=user.is_active,
#             organization_id=organization_id,
#             role=member.role,
#             created_at=user.created_at,
#             updated_at=user.updated_at
#         )

#     except NotFoundException:
#         raise
#     except Exception as e:
#         raise BadRequestException(f"Failed to update user role: {str(e)}")


def deactivate_user_service(
    user_id: UUID,
    organization_id: UUID,
) -> None:
    """
    Soft deletes a user by marking them inactive.
    Scoped to organization.
    """
    try:
        # Validate organization exists
        try:
            organization = Organizations.objects.get(id=organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        # Get user
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Deactivate user
        user.is_active = False
        user.save(update_fields=['is_active'])

        # Deactivate all memberships
        user.organization_memberships.filter(
            organization_id=organization_id
        ).update(is_active=False)

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to deactivate user: {str(e)}")


# ── Office profile services ────────────────────────────────

def create_office_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: OfficeProfileCreateSchema,
) -> OfficeProfileOutSchema:
    """
    Creates an office profile for a user.
    User must belong to the caller's organization.
    """
    try:
        # Validate user belongs to organization
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Check if profile already exists
        if OfficeProfile.objects.filter(user=user).exists():
            raise ConflictException(
                "Office profile already exists for this user"
            )

        # Create profile
        profile = OfficeProfile.objects.create(
            user=user,
            **data.dict()
        )

        return OfficeProfileOutSchema.from_orm(profile)

    except ConflictException:
        raise
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create office profile: {str(e)}")


def update_office_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: OfficeProfileUpdateSchema,
) -> OfficeProfileOutSchema:
    """
    Updates an existing office profile.
    User must belong to the caller's organization.
    """
    try:
        # Validate user belongs to organization
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Get profile
        try:
            profile = OfficeProfile.objects.get(user=user)
        except OfficeProfile.DoesNotExist:
            raise NotFoundException("Office profile not found")

        # Update profile
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.save()

        return OfficeProfileOutSchema.from_orm(profile)

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to update office profile: {str(e)}")


def get_office_profile_service(
    user_id: UUID,
    organization_id: UUID,
) -> OfficeProfileOutSchema:
    """Retrieves the office profile for a user."""
    try:
        # Validate user belongs to organization
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Get profile
        try:
            profile = OfficeProfile.objects.get(user=user)
        except OfficeProfile.DoesNotExist:
            raise NotFoundException("Office profile not found")

        return OfficeProfileOutSchema.from_orm(profile)

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to get office profile: {str(e)}")


# ── Driver profile services ────────────────────────────────

def create_driver_profile_service(
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
        # Validate user belongs to organization
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Check if profile already exists
        if DriverProfile.objects.filter(user=user).exists():
            raise ConflictException(
                "Driver profile already exists for this user"
            )

        # Create profile
        profile = DriverProfile.objects.create(
            user=user,
            **data.dict()
        )

        return DriverProfileOutSchema.from_orm(profile)

    except ConflictException:
        raise
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to create driver profile: {str(e)}")


def update_driver_profile_service(
    user_id: UUID,
    organization_id: UUID,
    data: DriverProfileUpdateSchema,
) -> DriverProfileOutSchema:
    """
    Updates an existing driver profile.
    User must belong to the caller's organization.
    """
    try:
        # Validate user belongs to organization
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Get profile
        try:
            profile = DriverProfile.objects.get(user=user)
        except DriverProfile.DoesNotExist:
            raise NotFoundException("Driver profile not found")

        # Update profile
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.save()

        return DriverProfileOutSchema.from_orm(profile)

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to update driver profile: {str(e)}")


def get_driver_profile_service(
    user_id: UUID,
    organization_id: UUID,
) -> DriverProfileOutSchema:
    """Retrieves the driver profile for a user."""
    try:
        # Validate user belongs to organization
        user = User.objects.filter(
            id=user_id,
            organization_memberships__organization_id=organization_id,
            organization_memberships__is_active=True
        ).first()

        if not user:
            raise NotFoundException("User not found in this organization")

        # Get profile
        try:
            profile = DriverProfile.objects.get(user=user)
        except DriverProfile.DoesNotExist:
            raise NotFoundException("Driver profile not found")

        return DriverProfileOutSchema.from_orm(profile)

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to get driver profile: {str(e)}")
