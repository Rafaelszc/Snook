import functools
import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import bcrypt

from snook.core.clock import from_iso, to_iso
from snook.core.errors import AppError
from snook.core.ratelimit import SlidingWindowLimiter
from snook.core.settings import Settings
from snook.core.text import normalize
from snook.core.uow import UnitOfWork
from snook.modules.auth import messages, repository
from snook.modules.auth.models import User, UserSession
from snook.modules.auth.schemas import PASSWORD_MAX_BYTES
from snook.modules.auth.schemas import is_valid_username as is_valid_username

SESSION_TOKEN_BYTES = 32

logger = logging.getLogger("snook.auth")


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


@dataclass(frozen=True)
class LoginThrottle:
    """Falhas de login por identificador normalizado e por IP do cliente (ADR-0010; SEC-06)."""

    by_identifier: SlidingWindowLimiter
    by_ip: SlidingWindowLimiter

    @classmethod
    def from_settings(cls, settings: Settings) -> "LoginThrottle":
        window = settings.login_window_seconds
        return cls(
            by_identifier=SlidingWindowLimiter(
                max_events=settings.login_max_failures, window_seconds=window
            ),
            by_ip=SlidingWindowLimiter(
                max_events=settings.login_max_failures_per_ip, window_seconds=window
            ),
        )


def _check_throttle(throttle: LoginThrottle, key: str, ip: str, now: datetime) -> None:
    for limiter_name, retry_after in (
        ("login_identifier", throttle.by_identifier.retry_after(key, now)),
        ("login_ip", throttle.by_ip.retry_after(ip, now)),
    ):
        if retry_after:
            logger.warning("security.rate_limited", extra={"limiter": limiter_name, "ip": ip})
            raise AppError(
                "rate_limited",
                messages.RATE_LIMITED,
                429,
                headers={"Retry-After": str(retry_after)},
            )


def login(
    uow: UnitOfWork,
    *,
    identifier: str,
    password: str,
    rounds: int,
    throttle: LoginThrottle,
    ip: str,
    now: datetime,
) -> AuthUser:
    """Login por email ou nome de usuário, sem caixa (`auth` 12 a 16).

    Toda falha responde a mesma mensagem e paga um bcrypt, inclusive conta inexistente
    e senha acima de 72 bytes: tempo parecido (SEC-05). Acima do limite de falhas, 429
    antes de olhar a senha (`auth` 27).
    """
    key = normalize(identifier)
    _check_throttle(throttle, key, ip, now)
    user = repository.find_user_by_login(uow.session, key)
    secret = password.encode()
    fits = len(secret) <= PASSWORD_MAX_BYTES
    hashed = user.password_hash.encode() if user and fits else _dummy_hash(rounds)
    matches = bcrypt.checkpw(secret if fits else b"", hashed)
    if user is None or not fits or not matches:
        throttle.by_identifier.hit(key, now)
        throttle.by_ip.hit(ip, now)
        logger.warning("auth.login_failed", extra={"reason": "bad_credentials", "ip": ip})
        raise AppError("invalid_credentials", messages.INVALID_CREDENTIALS, 401)
    # Zera só o identificador; o limite por IP segue contando (ADR-0010).
    throttle.by_identifier.reset(key)
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


def find_user_by_username(uow: UnitOfWork, username: str) -> AuthUser | None:
    """Normaliza e compara por `username_norm` (Q39); email não acha (SEC-24)."""
    user = repository.find_user_by_username(uow.session, normalize(username))
    return _public(user) if user is not None else None


def delete_user(uow: UnitOfWork, user_id: str) -> None:
    """Apaga o Usuário; sessões, configurações de LLM, Reuniões e derivados vão junto no
    mesmo commit (SEC-24). Arquivos em `/audios` ficam com `meetings.remove_meeting_files`."""
    repository.delete_user(uow.session, user_id)
