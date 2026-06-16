from asgiref.sync import sync_to_async
from config.exceptions import BadRequestException, UnauthorizedException
from django.contrib.auth import authenticate, get_user_model
from ninja_jwt.exceptions import TokenError
from ninja_jwt.tokens import RefreshToken

from app.access.auth import TokenManager
from app.access.models import TokenTypeChoices, VerificationTokens
from app.access.schema import (
    LoginResponseSchema,
    LoginSchema,
    RefreshTokenSchema,
    VerificationTokenResponseSchema,
    VerificationTokenSchema,
    VerificationTokenUpdateSchema,
    VerifyEmailSchema,
)

User = get_user_model()


async def create_email_verify_token_service(
    email: str,
) -> dict[str, str]:
    """Creates verification token"""
    user = await User.objects.aget(email=email)

    if user is None:
        raise User.DoesNotExist from None

    try:
        raw_token = await TokenManager.generate_token(
            user_id=str(user.id),
            token_type=TokenTypeChoices.EMAIL_VERIFICATION,
            expires_in=30,
        )
        return {
            "token": raw_token,
        }
    except ValueError as e:
        raise BadRequestException(str(e)) from e


async def verify_email_service(
    data: VerifyEmailSchema,
) -> VerificationTokenResponseSchema:
    """Verifies email"""
    try:
        verified_token = await TokenManager.verify_token(
            token=data.token, token_type=data.token_type
        )
        if not verified_token or isinstance(verified_token, bool):
            raise UnauthorizedException("Invalid or expired token") from None

        # Mark the token as used
        await TokenManager.mark_use(verified_token)
        return VerificationTokenResponseSchema(
            email=data.email,
            token=verified_token.token_hash,
            message="Email verified successfully",
        )
    except UnauthorizedException as e:
        raise UnauthorizedException(str(e)) from e
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_verification_token_service(
    token_id: int | None = None,
    token_type: str | None = None,
    user_id: int | None = None,
) -> list[VerificationTokenSchema] | VerificationTokenSchema:
    """Gets verification token by based on filter options"""
    filter_options: dict[str, int | str] = {}

    if token_id:
        filter_options["id"] = token_id
    if token_type:
        filter_options["token_type"] = token_type
    if user_id:
        filter_options["user_id"] = user_id

    try:
        token = await sync_to_async(
            lambda: VerificationTokens.objects.filter(
                **filter_options,
            ).first()
        )()

        # if token.isinstance(token, list):
        #     return [VerificationTokenSchema.from_orm(t).model_dump() for t in token]

        if token is None:
            raise VerificationTokens.DoesNotExist

        return VerificationTokenSchema.from_orm(token)
    except VerificationTokens.DoesNotExist as e:
        raise BadRequestException("Verification token not found") from e


async def update_verification_token_service(
    data: VerificationTokenUpdateSchema,
) -> VerificationTokenResponseSchema:
    pass


async def login_service(data: LoginSchema) -> LoginResponseSchema:
    """Logs in user"""
    user = await sync_to_async(
        lambda: authenticate(email=data.email, password=data.password)
    )()

    if user is None:
        raise UnauthorizedException("Invalid email or password") from None

    if not user.is_active:
        raise UnauthorizedException("User account is disabled") from None

    refresh = await sync_to_async(lambda: RefreshToken.for_user(user))()

    return LoginResponseSchema(
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
        token_type="bearer",
    )


async def refresh_token_service(data: RefreshTokenSchema) -> LoginResponseSchema:
    """Refreshes access token"""
    try:
        refresh = await sync_to_async(lambda: RefreshToken(data.refresh_token))()
        user = await User.objects.aget(id=refresh["user_id"])
    except (TokenError, User.DoesNotExist) as e:
        raise UnauthorizedException("Invalid or expired refresh token") from e

    new_refresh = await sync_to_async(lambda: RefreshToken.for_user(user))()

    return LoginResponseSchema(
        access_token=str(new_refresh.access_token),
        refresh_token=str(new_refresh),
        token_type="bearer",
    )
