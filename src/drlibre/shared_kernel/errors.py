from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    NO_ROOM_AVAILABLE = "no_room_available"
    NO_CLINICIAN_AVAILABLE = "no_clinician_available"
    INVALID_TRANSITION = "invalid_transition"
    HAS_DEPENDENTS = "has_dependents"
    RULE_VIOLATION = "rule_violation"

    @property
    def http_status(self) -> int:
        return _HTTP_STATUS[self]


_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.NO_ROOM_AVAILABLE: 409,
    ErrorCode.NO_CLINICIAN_AVAILABLE: 409,
    ErrorCode.INVALID_TRANSITION: 409,
    ErrorCode.HAS_DEPENDENTS: 409,
    ErrorCode.RULE_VIOLATION: 422,
}


class DomainError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
