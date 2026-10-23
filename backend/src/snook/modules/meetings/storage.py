"""Recepção do upload em streaming para `/audios/.tmp/<uuid>` (ADR-0018)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from fastapi import Request
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header

from snook.core.errors import AppError
from snook.modules.meetings import messages

FILE_FIELD = "file"
TEXT_FIELDS = ("title", "expected_speakers")
TEXT_FIELD_MAX_BYTES = 4096
# Cabeçalhos do multipart e campos de texto além do arquivo; o arquivo tem limite próprio.
MULTIPART_OVERHEAD_BYTES = 1024 * 1024


@dataclass
class ReceivedUpload:
    original_filename: str
    size_bytes: int
    fields: dict[str, str]


def too_large() -> AppError:
    return AppError("payload_too_large", messages.TOO_LARGE, 413)


def _invalid(name: str, message: str) -> AppError:
    return AppError("validation_error", messages.INVALID_DATA, 422, fields={name: message})


@dataclass
class _Part:
    headers: dict[bytes, bytes] = field(default_factory=dict)
    header_field: bytearray = field(default_factory=bytearray)
    header_value: bytearray = field(default_factory=bytearray)
    name: str = ""
    text: bytearray = field(default_factory=bytearray)


class _UploadSink:
    """Callbacks do parser: o arquivo vai ao disco em blocos; texto fica na memória, limitado."""

    def __init__(self, tmp_path: Path, max_bytes: int) -> None:
        self.tmp_path = tmp_path
        self.max_bytes = max_bytes
        self.part = _Part()
        self.file: BinaryIO | None = None
        self.filename: str | None = None
        self.size = 0
        self.fields: dict[str, str] = {}
        self.seen: set[str] = set()
        self.complete = False

    def on_part_begin(self) -> None:
        self.part = _Part()

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        self.part.header_field += data[start:end]

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        self.part.header_value += data[start:end]

    def on_header_end(self) -> None:
        name = bytes(self.part.header_field).lower()
        self.part.headers[name] = bytes(self.part.header_value)
        self.part.header_field.clear()
        self.part.header_value.clear()

    def on_headers_finished(self) -> None:
        disposition, options = parse_options_header(self.part.headers.get(b"content-disposition"))
        if disposition != b"form-data" or b"name" not in options:
            raise _invalid("body", messages.INVALID_DATA)
        name = options[b"name"].decode("utf-8", errors="replace")
        if name in self.seen:
            raise _invalid(name[:100], messages.FIELD_NOT_ALLOWED)
        self.seen.add(name)
        self.part.name = name
        if name == FILE_FIELD:
            if b"filename" not in options:
                raise _invalid(FILE_FIELD, messages.FILE_REQUIRED)
            # Bytes do cabeçalho como vieram; navegador manda o nome em UTF-8.
            self.filename = options[b"filename"].decode("utf-8", errors="replace")
            self.file = self.tmp_path.open("xb")
        elif name not in TEXT_FIELDS:
            raise _invalid(name[:100], messages.FIELD_NOT_ALLOWED)

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        chunk = data[start:end]
        if self.part.name == FILE_FIELD and self.file is not None:
            self.size += len(chunk)
            if self.size > self.max_bytes:
                raise too_large()
            self.file.write(chunk)
            return
        self.part.text += chunk
        if len(self.part.text) > TEXT_FIELD_MAX_BYTES:
            raise _invalid(self.part.name, messages.FIELD_TOO_LONG)

    def on_part_end(self) -> None:
        if self.part.name == FILE_FIELD and self.file is not None:
            self.file.close()
        elif self.part.name in TEXT_FIELDS:
            self.fields[self.part.name] = bytes(self.part.text).decode("utf-8", errors="replace")

    def on_end(self) -> None:
        self.complete = True

    def close(self) -> None:
        if self.file is not None and not self.file.closed:
            self.file.close()


async def receive_upload(request: Request, *, tmp_path: Path, max_bytes: int) -> ReceivedUpload:
    """Lê o multipart sem guardar o arquivo na memória. Quem chama apaga `tmp_path` sempre."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes + MULTIPART_OVERHEAD_BYTES:
        raise too_large()  # antes de ler o corpo
    content_type, options = parse_options_header(request.headers.get("content-type"))
    boundary = options.get(b"boundary")
    if content_type != b"multipart/form-data" or not boundary:
        raise _invalid(FILE_FIELD, messages.FILE_REQUIRED)

    sink = _UploadSink(tmp_path, max_bytes)
    parser = MultipartParser(
        boundary,
        {
            "on_part_begin": sink.on_part_begin,
            "on_header_field": sink.on_header_field,
            "on_header_value": sink.on_header_value,
            "on_header_end": sink.on_header_end,
            "on_headers_finished": sink.on_headers_finished,
            "on_part_data": sink.on_part_data,
            "on_part_end": sink.on_part_end,
            "on_end": sink.on_end,
        },
    )
    try:
        async for chunk in request.stream():
            parser.write(chunk)
        parser.finalize()
    except MultipartParseError:
        raise _invalid("body", messages.INVALID_DATA) from None
    finally:
        sink.close()
    if not sink.complete:  # corpo cortado antes do fim do multipart
        raise _invalid("body", messages.INVALID_DATA)
    if sink.filename is None:
        raise _invalid(FILE_FIELD, messages.FILE_REQUIRED)
    return ReceivedUpload(original_filename=sink.filename, size_bytes=sink.size, fields=sink.fields)
