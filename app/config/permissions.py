from asgiref.sync import sync_to_async
from functools import wraps

from httpx import request
from users.models import User
from config.exceptions import ForbiddenException, UnauthorizedException


# def require_roles(*allowed_role_names: str):
#     """
#     Checks that the authenticated user's role name is
#     in the allowed list.

#     Usage:
#         @router.post("/terminals", auth=JWTAuthBearer())
#         @require_roles(Role.RoleName.ORG_ADMIN, Role.RoleName.MANAGEMENT)
#         async def create_terminal(request, data):
#             ...
#     """
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(request, *args, **kwargs):
#             user = request.auth

#             if user is None:
#                 raise UnauthorizedException(
#                     "Authentication required"
#                 ) from None

#             if user.role is None:
#                 raise ForbiddenException(
#                     "No role assigned to this user"
#                 ) from None

#             if user.role.name not in allowed_role_names:
#                 raise ForbiddenException(
#                     "You do not have permission to perform this action"
#                 ) from None

#             return await func(request, *args, **kwargs)
#         return wrapper
#     return decorator

# config/permissions.py

from functools import wraps
from config.exceptions import UnauthorizedException, ForbiddenException

# config/permissions.py
from functools import wraps
from typing import Optional
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import models

from config.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    BadRequestException,
)
from organization.models import Organizations, OrganizationMember


User = get_user_model()


def require_roles(*allowed_role_names: str):
    """
    Decorator to check if the authenticated user has any of the allowed roles.
    Supports both old role system (User.role) and new organization-based roles.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get the authenticated user
            auth = request.auth or request.user

            if not auth:
                raise UnauthorizedException("Authentication required")

            # Get the user object
            try:
                user = User.objects.get(id=auth.id)
            except User.DoesNotExist:
                raise UnauthorizedException("User not found")

            # Superuser bypass - they can do everything
            if user.is_superuser:
                return func(request, *args, **kwargs)

            # Get organization_id
            organization = OrganizationMember.objects.filter(user=user).first()
            organization_id = kwargs.get('organization_id') or (organization.organization.id if organization else None)
            print(f"Checking roles for user {user.id} in organization {organization_id} with allowed roles {allowed_role_names}")

            if not organization_id and hasattr(request, 'organization_id'):
                organization_id = request.organization_id

            # If organization_id is provided, check user is a member with required role
            if organization_id:
                member = OrganizationMember.objects.filter(
                    user=user,
                    organization_id=organization_id,
                    is_active=True
                ).select_related('organization').first()

                if not member:
                    raise ForbiddenException(
                        f"User is not a member of this organization"
                    )

                # Convert both to lowercase for comparison
                if member.role.lower() not in [role.lower() for role in allowed_role_names]:
                    raise ForbiddenException(
                        f"Access denied. Required roles: {', '.join(allowed_role_names)}. "
                        f"User has role: {member.role}"
                    )

                # Set organization and member on request for later use
                request.organization = member.organization
                request.organization_member = member

                return func(request, *args, **kwargs)

            # No organization_id provided - just check if user has any of the roles globally
            # Check if user has a role (legacy or from somewhere else)
            if hasattr(user, 'role') and user.role:
                role_name = user.role.name if hasattr(user.role, 'name') else user.role
                if role_name.lower() in [role.lower() for role in allowed_role_names]:
                    return func(request, *args, **kwargs)

            raise ForbiddenException(
                f"Access denied. Required roles: {', '.join(allowed_role_names)}"
            )

        return wrapper
    return decorator


def require_organization_member():
    """
    Decorator to check if the authenticated user is a member of the organization
    specified in the request (via organization_id in kwargs or query params).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get the authenticated user
            auth = request.auth or request.user

            if not auth:
                raise UnauthorizedException("Authentication required")

            # Get the user object
            try:
                user = User.objects.get(id=auth.id)
            except User.DoesNotExist:
                raise UnauthorizedException("User not found")

            # Check superuser
            if user.is_superuser:
                return func(request, *args, **kwargs)

            # Get organization_id from kwargs or request
            organization_id = kwargs.get('organization_id')
            if not organization_id and hasattr(request, 'organization_id'):
                organization_id = request.organization_id

            if not organization_id:
                raise BadRequestException("Organization ID not provided")

            # Check if user is an active member
            try:
                member = OrganizationMember.objects.filter(
                    user=user,
                    organization_id=organization_id,
                    is_active=True
                ).select_related('organization').first()

                if not member:
                    raise ForbiddenException(
                        f"User is not a member of this organization"
                    )

                # Set organization and member on request
                request.organization = member.organization
                request.organization_member = member

                return func(request, *args, **kwargs)

            except Exception as e:
                raise ForbiddenException(f"Access denied: {str(e)}")

        return wrapper
    return decorator


def require_organization_admin():
    """
    Decorator to check if the authenticated user is an admin of the organization.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get the authenticated user
            auth = request.auth or request.user

            if not auth:
                raise UnauthorizedException("Authentication required")

            # Get the user object
            try:
                user = User.objects.get(id=auth.id)
            except User.DoesNotExist:
                raise UnauthorizedException("User not found")

            # Check superuser
            if user.is_superuser:
                return func(request, *args, **kwargs)

            # Get organization_id from kwargs or request
            organization_id = kwargs.get('organization_id')
            if not organization_id and hasattr(request, 'organization_id'):
                organization_id = request.organization_id

            if not organization_id:
                raise BadRequestException("Organization ID not provided")

            # Check if user is an org_admin
            try:
                member = OrganizationMember.objects.filter(
                    user=user,
                    organization_id=organization_id,
                    role='org_admin',
                    is_active=True
                ).select_related('organization').first()

                if not member:
                    raise ForbiddenException(
                        f"User is not an admin of this organization"
                    )

                # Set organization and member on request
                request.organization = member.organization
                request.organization_member = member

                return func(request, *args, **kwargs)

            except Exception as e:
                raise ForbiddenException(f"Access denied: {str(e)}")

        return wrapper
    return decorator


def require_organization_member_or_superuser():
    """
    Decorator that checks if user is either a superuser or a member of the organization.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get the authenticated user
            auth = request.auth or request.user

            if not auth:
                raise UnauthorizedException("Authentication required")

            # Get the user object
            try:
                user = User.objects.get(id=auth.id)
            except User.DoesNotExist:
                raise UnauthorizedException("User not found")

            # Superuser bypass
            if user.is_superuser:
                return func(request, *args, **kwargs)

            # Get organization_id from kwargs or request
            organization_id = kwargs.get('organization_id')
            if not organization_id and hasattr(request, 'organization_id'):
                organization_id = request.organization_id

            if not organization_id:
                raise BadRequestException("Organization ID not provided")

            # Check if user is a member
            try:
                member = OrganizationMember.objects.filter(
                    user=user,
                    organization_id=organization_id,
                    is_active=True
                ).select_related('organization').first()

                if not member:
                    raise ForbiddenException(
                        f"User is not a member of this organization"
                    )

                # Set organization and member on request
                request.organization = member.organization
                request.organization_member = member

                return func(request, *args, **kwargs)

            except Exception as e:
                raise ForbiddenException(f"Access denied: {str(e)}")

        return wrapper
    return decorator
