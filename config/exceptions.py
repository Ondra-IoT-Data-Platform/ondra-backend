from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, AuthorizationError, HttpError

from config.schema import MESSAGES, StatusCode, StatusMessage


class APIException(HttpError):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code=status_code, message=message)
        self.status_code = status_code
        self.message = message


class BadRequestException(APIException):
    def __init__(self, message: str | None = None):
        super().__init__(
            StatusCode.BAD_REQUEST.value,
            message or MESSAGES[StatusMessage.INVALID_INPUT],
        )


class NotFoundException(APIException):
    def __init__(self, message: str | None = None):
        super().__init__(
            StatusCode.NOT_FOUND.value,
            message or MESSAGES[StatusMessage.NOT_FOUND],
        )


class UnauthorizedException(APIException):
    def __init__(self, message: str | None = None):
        super().__init__(
            StatusCode.UNAUTHORIZED.value,
            message or MESSAGES[StatusMessage.UNAUTHORIZED],
        )


class ForbiddenException(APIException):
    def __init__(self, message: str | None = None):
        super().__init__(
            StatusCode.FORBIDDEN.value,
            message or MESSAGES[StatusMessage.FORBIDDEN],
        )


class InternalServerErrorException(APIException):
    def __init__(self, message: str | None = None):
        super().__init__(
            StatusCode.INTERNAL_SERVER_ERROR.value,
            message or MESSAGES[StatusMessage.INTERNAL_SERVER_ERROR],
        )


class ConflictException(APIException):
    def __init__(self, message: str | None = None):
        super().__init__(
            StatusCode.CONFLICT.value,
            message or MESSAGES[StatusMessage.CONFLICT],
        )


def register_exception_handlers(api: NinjaAPI) -> None:
    @api.exception_handler(APIException)
    def handle_api_exception(request: HttpRequest, exc: APIException) -> HttpResponse:
        return api.create_response(
            request,
            {
                "status": exc.status_code,
                "message": exc.message,
                "data": None,
                "error": None,
            },
            status=exc.status_code,
        )

    @api.exception_handler(AuthenticationError)
    def handle_auth_error(
        request: HttpRequest, exc: AuthenticationError
    ) -> HttpResponse:
        return api.create_response(
            request,
            {
                "status": StatusCode.UNAUTHORIZED.value,
                "message": MESSAGES[StatusMessage.UNAUTHORIZED],
                "data": None,
                "error": None,
            },
            status=StatusCode.UNAUTHORIZED.value,
        )

    @api.exception_handler(AuthorizationError)
    def handle_forbidden(request: HttpRequest, exc: AuthorizationError) -> HttpResponse:
        return api.create_response(
            request,
            {
                "status": StatusCode.FORBIDDEN.value,
                "message": MESSAGES[StatusMessage.FORBIDDEN],
                "data": None,
                "error": None,
            },
            status=StatusCode.FORBIDDEN.value,
        )

    @api.exception_handler(HttpError)
    def handle_http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        return api.create_response(
            request,
            {
                "status": exc.status_code,
                "message": str(exc),
                "data": None,
                "error": None,
            },
            status=exc.status_code,
        )
