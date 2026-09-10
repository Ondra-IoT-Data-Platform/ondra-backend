from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone

from access.auth_utils import OTokenManager, JWTManager, SMSManager
from access.models import UserSession
from access.schema import (
    LoginResponseSchema,
    LoginSchema,
    RefreshTokenResponseSchema,
)
from config.exceptions import BadRequestException, UnauthorizedException, NotFoundException
from organization.models import Organizations, OrganizationMember
from users.schema import UserOutSchema

User = get_user_model()



class AuthService:
    @staticmethod
    def login(
        payload: LoginSchema,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> LoginResponseSchema:
        """Authenticate a user and create a new session with access and refresh tokens."""
        user = authenticate(request=None, email=payload.email, password=payload.password)

        if user is None:
            raise UnauthorizedException("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedException(
                "Your account has been deactivated. Contact Admin"
            )

        if user.deleted_at is not None:
            raise UnauthorizedException("Invalid email or password.")

        org_member = OrganizationMember.objects.filter(user=user, is_active=True).first()

        role = org_member.role if org_member else 'NONE'

        # Generate tokens
        access_token, expires_in = JWTManager.generate_access_token(str(user.id), role)
        refresh_token, expires_at = JWTManager.generate_refresh_token(str(user.id), role)

        # Store hashed session
        UserSession.objects.create(
            user=user,
            refresh_token=OTokenManager._hash_token(refresh_token),
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
        )

        user.update_last_login()

        return LoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=UserOutSchema(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                organization_id=org_member.organization.id if org_member else None,
                role=role,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        )

    @staticmethod
    def refresh_token(refresh_token: str) -> RefreshTokenResponseSchema:
        """Issue a new access token from a valid refresh token."""
        payload = JWTManager.decode_refresh_token(refresh_token)
        user_id = payload.get("user_id")
        role = payload.get("role")

        session = UserSession.objects.filter(
            refresh_token=OTokenManager._hash_token(refresh_token),
            revoked_at__isnull=True,
        ).first()

        if not session or not session.is_valid:
            raise UnauthorizedException(
                "Refresh token is invalid or has expired."
            ) from None

        try:
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
        except User.DoesNotExist:
            raise UnauthorizedException("User not found.") from None

        access_token, expires_in = JWTManager.generate_access_token(str(user.id), role)

        # Update session activity
        with transaction.atomic():
            session.last_active_at = timezone.now()
            session.save(update_fields=["last_active_at"])

        return RefreshTokenResponseSchema(
            access_token=access_token,
            expires_in=expires_in,
        )

    @staticmethod
    def logout(refresh_token: str) -> None:
        """Revoke the current session."""
        session = UserSession.objects.filter(
            refresh_token=OTokenManager._hash_token(refresh_token),
            revoked_at__isnull=True,
        ).first()

        with transaction.atomic():
            if session:
                session.revoke()

    @staticmethod
    def logout_all(user_id: str) -> None:
        """Revoke all active sessions for a user — used on password change."""
        with transaction.atomic():
            UserSession.objects.filter(
                user_id=user_id,
                revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())


class SessionService:
    @staticmethod
    def revoke_all_sessions(user_id: str) -> None:
        """Called from UserService.change_password."""
        AuthService.logout_all(user_id)



# class OTPService:
#     @staticmethod
#     def request_otp(user: User, purpose: str) -> VerificationTokens:
#         """Create and send an OTP to the user's phone."""
#         valid_token_type = [tp.value for tp in VerificationTokens.token_type]
#         if purpose not in valid_token_type:
#             raise BadRequestException(
#                 f"Invalid OTP purpose. Must be one of: {valid_token_type}"
#             )

#         otp = OTokenManager.generate_otoken(user=user, purpose=purpose, expires_in=30)
#         SMSManager.send_otp_sms(phone_number=user.phone_number, token=otp.token, purpose=purpose)
#         return otp

#     @staticmethod
#     def verify_otp(phone_number: str, token: str, purpose: str) -> bool:
#         """Verify an OTP by phone number."""
#         try:
#             user = User.objects.get(phone_number=phone_number, deleted_at__isnull=True)
#         except User.DoesNotExist:
#             raise NotFoundException("User not found.") from None
#         return SMSManager.verify_otp(user=user, token=token, purpose=purpose)
