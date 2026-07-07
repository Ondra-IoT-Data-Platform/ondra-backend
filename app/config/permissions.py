from functools import wraps
from users.models import Role
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


def require_roles(*allowed_role_names: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            auth = request.auth

            if auth is None:
                raise UnauthorizedException(
                    "Authentication required"
                ) from None

            role_name = auth.get("role_name")

            if not role_name:
                raise ForbiddenException(
                    "No role assigned to this user"
                ) from None

            if role_name not in allowed_role_names:
                raise ForbiddenException(
                    "You do not have permission to perform this action"
                ) from None

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
