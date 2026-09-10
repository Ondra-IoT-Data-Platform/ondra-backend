# access/views.py
from uuid import UUID
from typing import Optional

from config.schema import (StatusCode, StatusMessage, create_response, BaseResponseSchema)
from config.permissions import require_roles
from access.schema import (
    LoginSchema,
    LoginResponseSchema,
    LogoutSchema,
    RefreshTokenSchema,
    OTPRequestSchema,
    OTPVerifySchema,
    OTPResponseSchema,
    OnboardingTokenGenerateSchema,
    OnboardingTokenResponseSchema,
    InvitationTokenGenerateSchema,
    InvitationTokenResponseSchema,
    TokenValidationSchema,
    TokenStatusResponseSchema,
    TokenRevokeSchema,
    TokenExtendSchema,
)

from access.auth_services import AuthService
from access.token_services import TokenService
from access.auth_utils import JWTAuthBearer

from django.db import transaction
from ninja import Router
from config.exceptions import (
    NotFoundException,
    UnauthorizedException,
    BadRequestException,
)
from users.schema import UserOutSchema


router = Router(tags=["Access"])
USER_MANAGERS = ["SUPERUSER", "ORG_ADMIN", "MANAGEMENT"]


# ── Authentication endpoints ──────────────────────────────────

@router.post(
    "/login",
    response=BaseResponseSchema,
    auth=None,
    summary="Login with Email and Password",
)
def login(request, payload: LoginSchema):
    """Login user and return access/refresh tokens."""
    device_info = request.META.get("HTTP_USER_AGENT")
    ip_address = request.META.get("REMOTE_ADDR")

    result = AuthService.login(
        payload=payload,
        device_info=device_info,
        ip_address=ip_address,
    )

    return create_response(
        data={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "expires_in": result.expires_in,
            "user": UserOutSchema.from_orm(result.user).dict(),
        },
        message="Login successful.",
    )


@router.post(
    "/token/refresh",
    response=BaseResponseSchema,
    auth=None,
    summary="Refresh access token",
)
@transaction.atomic()
def refresh_token(request, payload: RefreshTokenSchema):
    """Refresh access token using refresh token."""
    result = AuthService.refresh_token(payload.refresh_token)
    return create_response(
        data=result,
        message="Token refreshed successfully.",
    )


@router.post(
    "/logout",
    response=BaseResponseSchema,
    auth=JWTAuthBearer(),
    summary="Logout current session",
)
@transaction.atomic()
def logout(request, payload: LogoutSchema):
    """Logout user by revoking their session."""
    AuthService.logout(payload.refresh_token)
    return create_response(
        data=None,
        message="Logged out successfully.",
    )


# ── Onboarding Token endpoints ──────────────────────────────

@router.post(
    "/onboarding/generate-token",
    response=BaseResponseSchema,
    auth=JWTAuthBearer(),
    summary="Generate an onboarding token for a new user",
)
@require_roles("SUPERUSER", "ORG_ADMIN")
@transaction.atomic()
def generate_onboarding_token(request, payload: OnboardingTokenGenerateSchema):
    """
    Generate an onboarding token for a new user.
    The token is signed with the organization and returned to the browser.
    """
    try:
        result = TokenService.generate_organization_onboarding_token(payload)

        return create_response(
            data=result.dict(),
            message="Onboarding token generated successfully.",
            status_code=StatusCode.CREATED
        )
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except BadRequestException as e:
        raise BadRequestException(str(e))
    except Exception as e:
        raise BadRequestException(f"Failed to generate onboarding token: {str(e)}")


@router.post(
    "/onboarding/extend-token",
    response=BaseResponseSchema,
    auth=JWTAuthBearer(),
    summary="Extend onboarding token expiry",
)
@require_roles("SUPERUSER", "ORG_ADMIN")
def extend_onboarding_token(request, payload: TokenExtendSchema):
    """
    Extend the expiry of an onboarding token.
    """
    try:
        token_obj = TokenService.extend_token_expiry(payload)
        return create_response(
            data={
                "token_id": str(token_obj.id),
                "new_expires_at": token_obj.expires_at.isoformat(),
            },
            message="Token expiry extended successfully.",
            status_code=StatusCode.SUCCESS
        )
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except BadRequestException as e:
        raise BadRequestException(str(e))
    except Exception as e:
        raise BadRequestException(f"Failed to extend token: {str(e)}")


# ── Invitation Token endpoints ──────────────────────────────

@router.post(
    "/invitations/generate-token",
    response=BaseResponseSchema,
    auth=JWTAuthBearer(),
    summary="Generate an invitation token",
)
@require_roles("SUPERUSER", "ORG_ADMIN")
def generate_invitation_token(request, payload: InvitationTokenGenerateSchema):
    """
    Generate an invitation token for a new user to join an organization.
    """
    try:
        result = TokenService.generate_organization_invitation_token(payload)

        return create_response(
            data=result.dict(),
            message="Invitation token generated successfully.",
            status_code=StatusCode.CREATED
        )
    except NotFoundException as e:
        raise NotFoundException(str(e))
    except BadRequestException as e:
        raise BadRequestException(str(e))
    except Exception as e:
        raise BadRequestException(f"Failed to generate invitation token: {str(e)}")




# # ── OTP endpoints ────────────────────────────────────────────

# @router.post(
#     "/otp/request",
#     response=BaseResponseSchema,
#     auth=JWTAuthBearer(),
#     summary="Request an OTP",
# )
# @transaction.atomic()
# def request_otp(request, payload: OTPRequestSchema):
#     """Request an OTP for verification."""
#     otp = OTPService.request_otp(user=request.user, purpose=payload.purpose)
#     return create_response(
#         data={"expires_in": 300, "otp": otp},
#         message="OTP sent to your registered phone number.",
#     )


# @router.post(
#     "/otp/verify",
#     response=BaseResponseSchema,
#     auth=None,
#     summary="Verify OTP for account verification",
# )
# def verify_otp(request, payload: OTPVerifySchema):
#     """Verify OTP for account verification."""
#     OTPService.verify_otp(
#         phone_number=payload.phone_number,
#         token=payload.token,
#         purpose=payload.purpose,
#     )
#     return create_response(
#         data={"verified": True},
#         message="OTP verified successfully.",
#     )
