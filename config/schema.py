from enum import Enum
from typing import Generic, TypeVar

from ninja import Schema

# -----------------------------
# STATUS DEFINITIONS
# -----------------------------


class StatusCode(int, Enum):
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


class StatusMessage(str, Enum):
    SUCCESS = "SUCCESSFUL"
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CONFLICT = "CONFLICT"


MESSAGES: dict[StatusMessage, str] = {
    StatusMessage.SUCCESS: "Operation completed successfully.",
    StatusMessage.INVALID_INPUT: "The input provided is invalid.",
    StatusMessage.NOT_FOUND: "The requested resource was not found.",
    StatusMessage.UNAUTHORIZED: "You are not authorized to perform this action.",
    StatusMessage.FORBIDDEN: "You do not have permission to access this resource.",
    StatusMessage.INTERNAL_SERVER_ERROR: "An internal server error occurred.",
    StatusMessage.CONFLICT: "A conflict occurred with the current state of the resource.",
}

# -----------------------------
# GENERIC RESPONSE
# -----------------------------

DataT = TypeVar("DataT")


class BaseResponseSchema(Schema, Generic[DataT]):
    status: int
    message: str
    data: DataT | None = None
    error: str | None = None


# -----------------------------
# RESPONSE FACTORY
# -----------------------------


def create_response(
    data: DataT | None = None,
    error: str | None = None,
    status_code: StatusCode = StatusCode.OK,
    message: str | None = None,
) -> BaseResponseSchema[DataT]:
    if status_code == StatusCode.OK:
        return BaseResponseSchema(
            status=status_code.value,
            message=message or MESSAGES[StatusMessage.SUCCESS],
            data=data,
            error=None,
        )

    if status_code == StatusCode.CREATED:
        return BaseResponseSchema(
            status=status_code.value,
            message=message or MESSAGES[StatusMessage.SUCCESS],
            data=data,
            error=None,
        )

    return BaseResponseSchema(
        status=status_code.value,
        message=message
        or MESSAGES.get(
            StatusMessage.INTERNAL_SERVER_ERROR,
            "An error occurred.",
        ),
        data=None,
        error=error,
    )
