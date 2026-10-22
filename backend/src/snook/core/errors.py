import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("snook.errors")

_REQUIRED_MESSAGE = "Campo obrigatório."
_INVALID_MESSAGE = "Valor inválido."
_EXTRA_MESSAGE = "Campo não permitido."

_HTTP_CODES = {
    404: ("not_found", "Recurso não encontrado."),
    405: ("method_not_allowed", "Método não permitido."),
}


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        *,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.fields = fields
        self.headers = headers


def error_response(
    code: str,
    message: str,
    http_status: int,
    *,
    fields: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    return JSONResponse({"error": error}, status_code=http_status, headers=headers)


def _field_name(loc: tuple[int | str, ...]) -> str:
    parts = [str(part) for part in loc if part not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) or "body"


def _field_message(error_type: str) -> str:
    if error_type == "missing":
        return _REQUIRED_MESSAGE
    if error_type == "extra_forbidden":
        return _EXTRA_MESSAGE
    return _INVALID_MESSAGE


async def _handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    err = cast(AppError, exc)
    return error_response(
        err.code, err.message, err.http_status, fields=err.fields, headers=err.headers
    )


async def _handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    fields = {_field_name(err["loc"]): _field_message(err["type"]) for err in errors}
    return error_response("validation_error", "Dados inválidos.", 422, fields=fields)


async def _handle_http_exception(_request: Request, exc: Exception) -> JSONResponse:
    status = cast(StarletteHTTPException, exc).status_code
    code, message = _HTTP_CODES.get(status, ("http_error", "Requisição inválida."))
    return error_response(code, message, status)


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return error_response("internal_error", "erro interno", 500)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected)
