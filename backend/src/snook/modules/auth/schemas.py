import re

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from snook.core.errors import FIELD_MESSAGE_ERROR
from snook.modules.auth import messages

EMAIL_MAX = 254
PASSWORD_MIN_CHARS = 8
PASSWORD_MAX_BYTES = 72  # bcrypt ignora o que passa disso (ADR-0021)

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_USERNAME = re.compile(r"[A-Za-z0-9_.-]{3,30}")


def _invalid(message: str) -> PydanticCustomError:
    return PydanticCustomError(FIELD_MESSAGE_ERROR, message)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    username: str
    password: str

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        value = value.strip()
        if len(value) > EMAIL_MAX or not _EMAIL.fullmatch(value):
            raise _invalid(messages.EMAIL_INVALID)
        return value

    @field_validator("username")
    @classmethod
    def _check_username(cls, value: str) -> str:
        value = value.strip()
        if not _USERNAME.fullmatch(value):
            raise _invalid(messages.USERNAME_INVALID)
        return value

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        if len(value) < PASSWORD_MIN_CHARS:
            raise _invalid(messages.PASSWORD_TOO_SHORT)
        if len(value.encode()) > PASSWORD_MAX_BYTES:
            raise _invalid(messages.PASSWORD_TOO_LONG)
        return value


class UserOut(BaseModel):
    id: str
    email: str
    username: str
