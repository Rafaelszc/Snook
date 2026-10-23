from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from snook.modules.auth.models import User, UserSession


def email_taken(session: Session, email_norm: str) -> bool:
    return session.scalar(select(User.id).where(User.email_norm == email_norm)) is not None


def username_taken(session: Session, username_norm: str) -> bool:
    return session.scalar(select(User.id).where(User.username_norm == username_norm)) is not None


def add_user(session: Session, user: User) -> None:
    session.add(user)
    session.flush()


def get_user(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def find_user_by_login(session: Session, identifier_norm: str) -> User | None:
    """Email ou nome de usuário. Nome não aceita `@`, email exige: não colidem."""
    return session.scalar(
        select(User).where(
            or_(User.email_norm == identifier_norm, User.username_norm == identifier_norm)
        )
    )


def add_session(session: Session, row: UserSession) -> None:
    session.add(row)
    session.flush()


def get_session(session: Session, token_hash: str) -> UserSession | None:
    return session.get(UserSession, token_hash)


def delete_session(session: Session, token_hash: str) -> None:
    session.execute(delete(UserSession).where(UserSession.token_hash == token_hash))


def delete_expired_sessions(session: Session, now_iso: str, idle_cutoff_iso: str) -> int:
    """Apaga sessões além do máximo (`expires_at`) ou inativas desde antes do corte."""
    result = session.execute(
        delete(UserSession).where(
            or_(UserSession.expires_at <= now_iso, UserSession.last_seen_at <= idle_cutoff_iso)
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)
