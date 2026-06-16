from config.exceptions import (
    NotFoundException,
    UnauthorizedException,
)
from config.schema import StatusCode, StatusMessage, create_response
from ninja import Router

from app.access.schema import (
    LoginSchema,
    RefreshTokenSchema,
    VerificationTokenSchema,
    VerificationTokenUpdateSchema,
    VerifyEmailSchema,
)
from app.access.services import (
    create_email_verify_token_service,
    get_verification_token_service,
    login_service,
    refresh_token_service,
    update_verification_token_service,
    verify_email_service,
)

router = Router(tags=["Access"])


@router.post("/login")
async def login(data: LoginSchema) -> dict[str, str]:
    """Logs in user"""
    try:
        result = await login_service(data)
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except UnauthorizedException as e:
        raise UnauthorizedException(str(e)) from e


@router.post("/refresh")
async def refresh_token(data: RefreshTokenSchema) -> dict[str, str]:
    """Refreshes access token"""
    try:
        result = await refresh_token_service(data)
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except UnauthorizedException as e:
        raise UnauthorizedException(str(e)) from e


@router.get("/token/")
async def get_verification_token(
    token_id: int | None = None,
    token_type: str | None = None,
    user_id: int | None = None,
) -> dict[str, str]:
    """Gets a verification token for the user"""
    try:
        result = await get_verification_token_service(
            token_id=token_id, token_type=token_type, user_id=user_id
        )
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


@router.post("/email/token")
async def create_email_verification_token(
    email: str,
) -> dict[str, str]:
    """Creates an email verification token"""
    try:
        result = await create_email_verify_token_service(email)
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


@router.post("/email/token/verify")
async def verify_email_token(data: VerifyEmailSchema) -> dict[str, str]:
    """Verifies an email verification token"""
    try:
        result = await verify_email_service(data)
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


@router.post("/verification/token")
async def create_verification_token(data: VerificationTokenSchema) -> dict[str, str]:
    """Creates a verification token"""
    try:
        result = await create_verification_token(data)
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e


@router.patch("/verification/token")
async def update_verification_token(
    data: VerificationTokenUpdateSchema,
) -> dict[str, str]:
    """Updates a verification token"""
    try:
        result = await update_verification_token_service(data)
        return create_response(
            status_code=StatusCode.SUCCESS,
            message=StatusMessage.SUCCESS,
            data=result,
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
