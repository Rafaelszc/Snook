import functools
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import bcrypt

from snook.core.clock import from_iso, to_iso
from snook.core.errors import AppError
from snook.core.text import normalize
from snook.core.uow import UnitOfWork
from snook.modules.auth import messages, repository
from snook.modules.auth.models import User, UserSession
from snook.modules.auth.schemas import PASSWORD_MAX_BYTES

SESSION_TOKEN_BYTES = 32


@dataclass(frozen=True)
class AuthUser:
    """Usuário autenticado entregue aos demais módulos (`current_user`)."""

    id: str
    email: str
    username: str


def _public(user: User) -> AuthUser:
    return AuthUser(id=user.id, email=user.email, username=user.username)


def hash_password(password: str, rounds: int) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def register_user(
    uow: UnitOfWork, *, email: str, username: str, password: str, rounds: int, now: datetime
) -> AuthUser:
    """Cria o Usuário. Email e nome de usuário únicos sem caixa (`auth` 3, 4, 6)."""
    email_norm, username_norm = normalize(email), normalize(username)
    if repository.email_taken(uow.session, email_norm):
        raise AppError(
            "email_taken", messages.EMAIL_TAKEN, 409, fields={"email": messages.EMAIL_TAKEN}
        )
    if repository.username_taken(uow.session, username_norm):
        raise AppError(
            "username_taken",
            messages.USERNAME_TAKEN,
            409,
            fields={"username": messages.USERNAME_TAKEN},
        )
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_norm=email_norm,
        username=username,
        username_norm=username_norm,
        password_hash=hash_password(password, rounds),
        created_at=to_iso(now),
    )
    repository.add_user(uow.session, user)
    return _public(user)


@functools.cache
def _dummy_hash(rounds: int) -> bytes:
    return bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt(rounds))


def login(uow: UnitOfWork, *, identifier: str, password: str, rounds: int) -> AuthUser:
    """Login por email ou nome de usuário, sem caixa (`auth` 12 a 16).

    Toda falha responde a mesma mensagem e paga um bcrypt, inclusive conta inexistente
    e senha acima de 72 bytes: tempo parecido (SEC-05).
    """
    user = repository.find_user_by_login(uow.session, normalize(identifier))
    secret = password.encode()
    fits = len(secret) <= PASSWORD_MAX_BYTES
    hashed = user.password_hash.encode() if user and fits else _dummy_hash(rounds)
    matches = bcrypt.checkpw(secret if fits else b"", hashed)
    if user is None or not fits or not matches:
        raise AppError("invalid_credentials", messages.INVALID_CREDENTIALS, 401)
    return _public(user)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(uow: UnitOfWork, user_id: str, *, now: datetime, max_seconds: int) -> str:
    """Token novo a cada cadastro e login; o banco guarda só o SHA-256 (SEC-03)."""
    token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    repository.add_session(
        uow.session,
        UserSession(
            token_hash=_token_hash(token),
            user_id=user_id,
            created_at=to_iso(now),
            last_seen_at=to_iso(now),
            expires_at=to_iso(now + timedelta(seconds=max_seconds)),
        ),
    )
    return token


def authenticate_session(
    uow: UnitOfWork, token: str, *, now: datetime, idle_seconds: int
) -> AuthUser | None:
    """Usuário da sessão, ou `None` se ausente, vencida ou inativa. Vencida é apagada."""
    token_hash = _token_hash(token)
    row = repository.get_session(uow.session, token_hash)
    if row is None:
        return None
    idle_limit = from_iso(row.last_seen_at) + timedelta(seconds=idle_seconds)
    if now >= from_iso(row.expires_at) or now >= idle_limit:
        repository.delete_session(uow.session, token_hash)
        return None
    user = repository.get_user(uow.session, row.user_id)
    if user is None:
        return None
    row.last_seen_at = to_iso(now)
    return _public(user)


def delete_session(uow: UnitOfWork, token: str) -> None:
    """Logout: apaga a sessão no servidor (SEC-03)."""
    repository.delete_session(uow.session, _token_hash(token))


def delete_expired_sessions(uow: UnitOfWork, *, now: datetime, idle_seconds: int) -> int:
    idle_cutoff = now - timedelta(seconds=idle_seconds)
    return repository.delete_expired_sessions(uow.session, to_iso(now), to_iso(idle_cutoff))
