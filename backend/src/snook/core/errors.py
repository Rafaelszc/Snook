import logging
from collections.abc import Mapping
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("snook.errors")

_REQUIRED_MESSAGE = "Campo obrigatório."
_INVALID_MESSAGE = "Valor inválido."
_EXTRA_MESSAGE = "Campo não permitido."

# Tipo de `PydanticCustomError` cuja mensagem (pt-BR, de `messages.py`) vai direto ao `fields`.
FIELD_MESSAGE_ERROR = "field_message"

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
        details: Mapping[str, int | str] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.fields = fields
        self.headers = headers
        self.details = details


def error_response(
    code: str,
    message: str,
    http_status: int,
    *,
    fields: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    details: Mapping[str, int | str] | None = None,
) -> JSONResponse:
    """`details`: campos extras ao lado de `code` (ex.: `part_index` em `part_too_large`)."""
    error: dict[str, Any] = {**(details or {}), "code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    return JSONResponse({"error": error}, status_code=http_status, headers=headers)


def _field_name(loc: tuple[int | str, ...]) -> str:
    parts = [str(part) for part in loc if part not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) or "body"


def _field_message(error_type: str, message: str) -> str:
    if error_type == FIELD_MESSAGE_ERROR:
        return message
    if error_type == "missing":
        return _REQUIRED_MESSAGE
    if error_type == "extra_forbidden":
        return _EXTRA_MESSAGE
    return _INVALID_MESSAGE


async def _handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    err = cast(AppError, exc)
    return error_response(
        err.code,
        err.message,
        err.http_status,
        fields=err.fields,
        headers=err.headers,
        details=err.details,
    )


async def _handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    fields = {_field_name(err["loc"]): _field_message(err["type"], err["msg"]) for err in errors}
    return error_response("validation_error", "Dados inválidos.", 422, fields=fields)


async def _handle_http_exception(_request: Request, exc: Exception) -> JSONResponse:
    status = cast(StarletteHTTPException, exc).status_code
    code, message = _HTTP_CODES.get(status, ("http_error", "Requisição inválida."))
    return error_response(code, message, status)


def register_error_handlers(
    app: FastAPI, *, server_error_headers: Mapping[str, str] | None = None
) -> None:
    """`server_error_headers`: o 500 sai por fora dos middlewares da app e precisa deles aqui."""

    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
        headers = dict(server_error_headers) if server_error_headers else None
        return error_response("internal_error", "erro interno", 500, headers=headers)

    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected)
