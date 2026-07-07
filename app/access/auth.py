import hashlib
import secrets
from datetime import timedelta
from typing import Any, Optional

from asgiref.sync import sync_to_async
from config.exceptions import UnauthorizedException
from django.contrib.auth import get_user_model
from django.utils import timezone
from ninja_jwt.authentication import (
    JWTAuth as BaseJWTAuth,
)
from ninja import Schema
from ninja.security import HttpBearer
from ninja_jwt.tokens import AccessToken
from ninja_jwt.exceptions import TokenError

from access.models import VerificationTokens

User = get_user_model()


class JWTAuthBearer(HttpBearer):
    """
    Reads custom claims from the validated JWT.
    Attaches a lightweight user context to request.auth
    without a database query on every authenticated request.
    """

    async def authenticate(self, request, token: str) -> Optional[Any]:
        try:
            validated_token = AccessToken(token)

            # Read custom claims we added in get_token
            return {
                "user_id": validated_token["user_id"],
                "org_id": validated_token.get("org_id"),
                "role_id": validated_token.get("role_id"),
                "role_name": validated_token.get("role_name"),
                "is_superuser": validated_token.get("is_superuser")
            }

        except TokenError:
            return None

class TokenManager:
    """Create and hash tokens for email verification and etcetcera"""

    @staticmethod
    async def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    async def generate_token(
        cls, user_id: str, token_type: str, expires_in: int = 60
    ) -> str:
        """Create a token for a user"""
        if await sync_to_async(
            lambda: VerificationTokens.objects.filter(
                user_id=user_id, token_type=token_type, is_used=False
            ).exists()
        )():
            raise ValueError(
                "A valid token already exists for this user and token type"
            )

        raw_token = secrets.token_urlsafe(32)
        token_hash = await cls._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(minutes=expires_in)
        await VerificationTokens.objects.acreate(
            token_hash=token_hash,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
        )
        return raw_token

    @classmethod
    async def verify_token(
        cls, token: str, token_type: str
    ) -> bool | VerificationTokens:
        """Verify a token and mark it as used"""
        token_hash = await cls._hash_token(token)
        token_obj = await sync_to_async(
            lambda: VerificationTokens.objects.filter(
                token_hash=token_hash, token_type=token_type, is_used=False
            ).first()
        )()

        if not token_obj:
            return False

        if token_obj.expires_at < timezone.now():
            return False

        return token_obj

    @staticmethod
    async def mark_use(token_obj: VerificationTokens) -> None:
        """Mark a token as used"""
        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])
