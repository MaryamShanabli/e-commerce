import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


class AppException(Exception):
    status_code: int = 500
    error_type: str = "InternalServerError"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    status_code = 404
    error_type = "NotFoundException"


class BadRequestException(AppException):
    status_code = 400
    error_type = "BadRequestException"


class ConflictException(AppException):
    status_code = 409
    error_type = "ConflictException"


class UnauthorizedException(AppException):
    status_code = 401
    error_type = "UnauthorizedException"


class ForbiddenException(AppException):
    status_code = 403
    error_type = "ForbiddenException"


class ValidationException(AppException):
    status_code = 400
    error_type = "ValidationError"


def _error_body(message: str, status_code: int, error_type: str) -> dict:
    return {
        "message": message,
        "status_code": status_code,
        "error_type": error_type,
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
    }


def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.message, exc.status_code, exc.error_type),
    )


def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        f"{'.'.join(str(p) for p in err['loc']) if err.get('loc') else 'body'}: {err['msg']}"
        for err in exc.errors()
    ]
    message = "; ".join(details)
    return JSONResponse(
        status_code=400,
        content=_error_body(message, 400, "ValidationError"),
    )


def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body("Internal server error", 500, "InternalServerError"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)


def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    error_type = {
        400: "BadRequestException",
        401: "UnauthorizedException",
        403: "ForbiddenException",
        404: "NotFoundException",
        409: "ConflictException",
    }.get(exc.status_code, "HTTPException")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(str(exc.detail), exc.status_code, error_type),
    )
