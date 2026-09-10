# access/auth_utils.py
import secrets
import hashlib
import random
from datetime import timedelta
from typing import Optional, Tuple

import jwt
from ninja.security import HttpBearer
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from config.exceptions import UnauthorizedException
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from access.models import OrganizationTokens, TokenTypeChoices
from users.models import User


# ====== JWT EXPIRY TIME =========
ACCESS_TOKEN_EXPIRY_MINUTES = 60
REFRESH_TOKEN_EXPIRY_DAYS = 7

# ====== OTP EXPIRY TIME =========
OTP_EXPIRY_MINUTES = 30
MAX_OTP_ATTEMPTS = 3


User = get_user_model()



class JWTAuthBearer(HttpBearer):
    """
    JWT Authentication validator.
    Attach to any endpoint that requires authentication:
        @router.get("/me", auth=JWTAuth())
    """

    def authenticate(self, request, token: str):
        payload = JWTManager.decode_access_token(token)
        user_id = payload.get("user_id")

        try:
            user = User.objects.get(
                id=user_id,
                is_active=True,
                deleted_at__isnull=True,
            )
        except User.DoesNotExist:
            raise UnauthorizedException("User not found or inactive.") from None

        request.user = user
        return user


class OTokenManager:
    """Create and hash tokens for email verification, onboarding, etc."""

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def _generate_short_code(length: int = 6) -> str:
        """Generate a numeric short code for OTP."""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    @classmethod
    def generate_otoken(
        cls,
        user_id: str,
        token_type: str,
        expires_in_minutes: int = 30,
        organization_id: Optional[str] = None,
        email: Optional[str] = None
    ) -> Tuple[str, OrganizationTokens]:
        """
        Generate a token for a user.

        Args:
            user_id: User UUID
            token_type: Type of token (from TokenTypeChoices)
            expires_in_minutes: Token expiration in minutes
            organization_id: Optional organization ID
            email: Optional email (for invitation tokens)

        Returns:
            Tuple[str, OrganizationTokens]: (raw_token, token_object)
        """
        # Check for existing valid token
        existing_token = OrganizationTokens.objects.filter(
            user_id=user_id,
            token_type=token_type,
            is_used=False,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_token:
            raise ValidationError(
                f"A valid {token_type} token already exists for this user"
            )

        # Generate token
        raw_token = cls._generate_secure_token()
        token_hash = cls._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)

        # Get user
        user = User.objects.get(id=user_id)

        # Create token record
        token_obj = OrganizationTokens.objects.create(
            token=raw_token,
            token_hash=token_hash,
            user=user,
            token_type=token_type,
            email=email or user.email,
            organization_id=organization_id,
            expires_at=expires_at,
            is_used=False,
            is_revoked=False,
            metadata={}
        )

        return raw_token, token_obj

    @classmethod
    def generate_otp(cls, user_id: str, expires_in_minutes: int = 10) -> Tuple[str, OrganizationTokens]:
        """
        Generate a numeric OTP for two-factor authentication.

        Args:
            user_id: User UUID
            expires_in_minutes: OTP expiration in minutes

        Returns:
            Tuple[str, OrganizationTokens]: (otp_code, token_object)
        """
        # Check for existing valid OTP
        existing_token = OrganizationTokens.objects.filter(
            user_id=user_id,
            token_type=TokenTypeChoices.TWO_FACTOR_AUTH,
            is_used=False,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_token:
            raise ValidationError("A valid OTP already exists for this user")

        # Generate numeric OTP
        otp_code = cls._generate_short_code(length=6)
        token_hash = cls._hash_token(otp_code)
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)

        # Get user
        user = User.objects.get(id=user_id)

        # Create token record
        token_obj = OrganizationTokens.objects.create(
            token=otp_code,
            token_hash=token_hash,
            user=user,
            token_type=TokenTypeChoices.TWO_FACTOR_AUTH,
            email=user.email,
            expires_at=expires_at,
            is_used=False,
            is_revoked=False,
            metadata={
                'otp_type': 'numeric',
                'attempts': 0,
                'max_attempts': MAX_OTP_ATTEMPTS
            }
        )

        return otp_code, token_obj

    @classmethod
    def verify_otoken(cls, token: str, token_type: str) -> Optional[OrganizationTokens]:
        """
        Verify a token and return the token object if valid.

        Args:
            token: Raw token string
            token_type: Type of token to verify

        Returns:
            Optional[OrganizationTokens]: Token object if valid, None otherwise
        """
        token_hash = cls._hash_token(token)

        try:
            token_obj = OrganizationTokens.objects.get(
                token_hash=token_hash,
                token_type=token_type,
                is_used=False,
                is_revoked=False,
                expires_at__gt=timezone.now()
            )
            return token_obj
        except OrganizationTokens.DoesNotExist:
            return None

    @classmethod
    def verify_otp(cls, otp_code: str, user_id: str) -> Optional[OrganizationTokens]:
        """
        Verify an OTP for a specific user.

        Args:
            otp_code: Numeric OTP code
            user_id: User UUID

        Returns:
            Optional[OrganizationTokens]: Token object if valid, None otherwise
        """
        token_hash = cls._hash_token(otp_code)

        try:
            token_obj = OrganizationTokens.objects.get(
                token_hash=token_hash,
                user_id=user_id,
                token_type=TokenTypeChoices.TWO_FACTOR_AUTH,
                is_used=False,
                is_revoked=False,
                expires_at__gt=timezone.now()
            )
            return token_obj
        except OrganizationTokens.DoesNotExist:
            return None

    @staticmethod
    def mark_used(token_obj: OrganizationTokens) -> None:
        """Mark a token as used."""
        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])

    @staticmethod
    def mark_revoked(token_obj: OrganizationTokens, reason: Optional[str] = None) -> None:
        """Revoke a token."""
        token_obj.is_revoked = True
        if reason:
            token_obj.metadata = {
                **(token_obj.metadata or {}),
                'revoked_reason': reason,
                'revoked_at': timezone.now().isoformat()
            }
            token_obj.save(update_fields=["is_revoked", "metadata"])
        else:
            token_obj.save(update_fields=["is_revoked"])

    @staticmethod
    def is_token_valid(token_obj: OrganizationTokens) -> bool:
        """Check if a token is valid."""
        return (
            not token_obj.is_used and
            not token_obj.is_revoked and
            token_obj.expires_at > timezone.now()
        )

    @classmethod
    def generate_invitation_token(
        cls,
        organization_id: str,
        email: str,
        role: str = 'member',
        expires_in_hours: int = 72,
        invited_by_id: Optional[str] = None
    ) -> Tuple[str, OrganizationTokens]:
        """
        Generate an invitation token for a new user.

        Args:
            organization_id: Organization UUID
            email: User's email
            role: Role to assign
            expires_in_hours: Token expiration in hours
            invited_by_id: User ID of the inviter

        Returns:
            Tuple[str, OrganizationTokens]: (raw_token, token_object)
        """
        # Check if user already exists
        if User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError(f"User with email {email} already exists")

        # Check for existing valid invitation
        existing_token = OrganizationTokens.objects.filter(
            organization_id=organization_id,
            email=email,
            token_type=TokenTypeChoices.INVITATION,
            is_used=False,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_token:
            raise ValidationError("A valid invitation already exists for this email")

        # Generate token
        raw_token = cls._generate_secure_token()
        token_hash = cls._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)

        # Create token record
        token_obj = OrganizationTokens.objects.create(
            token=raw_token,
            token_hash=token_hash,
            token_type=TokenTypeChoices.INVITATION,
            email=email,
            user=None,  # User not created yet
            organization_id=organization_id,
            expires_at=expires_at,
            is_used=False,
            is_revoked=False,
            metadata={
                'role': role,
                'invited_by': invited_by_id,
                'invited_at': timezone.now().isoformat()
            }
        )

        return raw_token, token_obj

    @classmethod
    def generate_onboarding_token(
        cls,
        organization_id: str,
        email: str,
        expires_in_hours: int = 24,
        metadata: Optional[dict] = None
    ) -> Tuple[str, OrganizationTokens]:
        """
        Generate an onboarding token for an existing user.

        Args:
            organization_id: Organization UUID
            email: User's email
            expires_in_hours: Token expiration in hours
            metadata: Additional metadata

        Returns:
            Tuple[str, OrganizationTokens]: (raw_token, token_object)
        """
        # user = User.objects.get(id=user_id)

        # Check for existing valid onboarding token
        existing_token = OrganizationTokens.objects.filter(
            organization_id=organization_id,
            email=email,
            token_type=TokenTypeChoices.USER_ONBOARDING,
            is_used=False,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_token:
            raise ValidationError("A valid onboarding token already exists for this user")

        # Generate token
        raw_token = cls._generate_short_code(length=6)
        token_hash = cls._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)

        with transaction.atomic():
            # Create token record
            token_obj = OrganizationTokens.objects.create(
                token=raw_token,
                token_hash=token_hash,
                token_type=TokenTypeChoices.USER_ONBOARDING,
                email=email,
                organization_id=organization_id,
                expires_at=expires_at,
                is_used=False,
                is_revoked=False,
                metadata=metadata or {}
            )

        return raw_token, token_obj


class JWTManager:
    """JWT token management utilities."""

class JWTManager:
    @classmethod
    def generate_access_token(cls, user_id: str, role: str) -> tuple[str, int]:
        """Generate a JWT access token. Returns (token, expires_in_seconds)."""
        expires_in = ACCESS_TOKEN_EXPIRY_MINUTES * 60
        payload = {
            "user_id": str(user_id),
            "role": role,
            "type": "access",
            "iat": timezone.now(),
            "exp": timezone.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return token, expires_in

    @classmethod
    def generate_refresh_token(cls, user_id: str, role: str) -> tuple[str, object]:
        """Generate a JWT refresh token. Returns (token, expires_at)."""
        expires_at = timezone.now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        payload = {
            "user_id": str(user_id),
            "role": role,
            "type": "refresh",
            "iat": timezone.now(),
            "exp": expires_at,
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return token, expires_at

    @classmethod
    def decode_access_token(cls, token: str) -> dict:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            if payload.get("type") != "access":
                raise UnauthorizedException("Invalid token type.") from None
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Access token has expired.") from None
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid access token.") from None

    @classmethod
    def decode_refresh_token(cls, token: str) -> dict:
        """Decode and validate a JWT refresh token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid token type.")
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Refresh token has expired.") from None
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid refresh token.") from None


    @staticmethod
    def get_user_from_token(token: str):
        """Get user from JWT token."""
        payload = JWTManager.decode_token(token)
        user_id = payload.get('user_id')

        if not user_id:
            raise ValidationError("Invalid token payload")

        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise ValidationError("User not found")




class SMSManager:
    """SMS utilities for OTP delivery."""

    @staticmethod
    def send_otp(phone_number: str, otp_code: str) -> bool:
        """
        Send OTP via SMS.
        Placeholder - implement with your SMS provider.
        """
        # Example with Twilio
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=f"Your verification code is: {otp_code}",
        #     from_=twilio_phone_number,
        #     to=phone_number
        # )
        # return message.sid is not None

        print(f"Sending OTP {otp_code} to {phone_number}")  # Placeholder
        return True

    @staticmethod
    def send_verification_code(phone_number: str, code: str) -> bool:
        """Send verification code via SMS."""
        return SMSManager.send_otp(phone_number, code)
