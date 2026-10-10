"""Application errors and their HTTP representation.

Every error response has the shape ``{"error": {"code": ..., "message": ...}}``.
Messages are safe to show to clients; diagnostics go to the server log.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Internal server error"

    def __init__(self, message: str | None = None, *, headers: dict[str, str] | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.headers = headers


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_required"
    message = "Authentication required"

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Request conflicts with the current state"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "A required service is unavailable"


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    message = "The request could not be processed"

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"
    message = "The uploaded file is too large"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests. Please wait a moment and try again."


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
    message = "An external service failed to respond"


def _error_response(status_code: int, code: str, message: str, *, headers=None, details=None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only location, message and type are returned; submitted values are not echoed.
        details = [
            {"loc": [str(part) for part in error["loc"]], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return _error_response(422, "validation_error", "Request validation failed", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(exc.status_code, "http_error", str(exc.detail), headers=exc.headers)

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    async def handle_database_unavailable(_: Request, exc: Exception) -> JSONResponse:
        logger.error("database unavailable: %s", type(exc).__name__)
        return _error_response(503, "database_unavailable", "The database is unavailable")

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return _error_response(500, "internal_error", "Internal server error")
