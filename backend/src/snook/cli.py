"""Comandos do Operador: `python -m snook.cli <comando>`.

Comando que escreve no banco roda com o backend parado: pega a trava `/data/snook.lock`
(ADR-0006, SEC-24).
"""

import argparse
import logging
import sys
from collections.abc import Sequence

from snook.core.clock import SystemClock
from snook.core.db import backup_database, create_db_engine, create_session_factory
from snook.core.files import UnsafePathError
from snook.core.logging import setup_logging
from snook.core.runlock import RunLock, RunLockError
from snook.core.settings import Settings, SettingsError, load_settings
from snook.core.uow import UnitOfWork
from snook.modules.auth import service as auth_service
from snook.modules.diarized_transcription import service as transcription_service
from snook.modules.diarized_transcription.engines.base import EngineFailure
from snook.modules.llm_providers import service as llm_service
from snook.modules.llm_providers.crypto import KeyCipher, decode_master_key
from snook.modules.meetings import service as meetings_service

logger = logging.getLogger("snook.cli")


class CommandError(Exception):
    """Falha esperada do comando; a mensagem vai para o Operador, sem segredo."""


def _rotate_master_key(settings: Settings) -> None:
    if settings.snook_master_key_previous is None:
        raise CommandError("SNOOK_MASTER_KEY_PREVIOUS ausente: informe a chave-mestra anterior.")
    cipher = KeyCipher(
        decode_master_key(settings.snook_master_key.get_secret_value()),
        previous=decode_master_key(settings.snook_master_key_previous.get_secret_value()),
    )
    db = settings.database_path
    if not db.exists():
        raise CommandError(f"banco {db} não existe: suba o backend uma vez antes.")
    with RunLock(db.with_name("snook.lock")):
        backup = db.with_name(f"{db.name}.bak-rotate")
        backup_database(db, backup)
        engine = create_db_engine(db)
        try:
            with UnitOfWork(create_session_factory(engine), lambda _event: None) as uow:
                result = llm_service.rotate_master_key(uow, cipher, now=SystemClock().now())
        finally:
            engine.dispose()
    logger.info(
        "operator.master_key_rotated",
        extra={"rotated": result.rotated, "unreadable": result.unreadable},
    )
    print(f"Chaves recifradas: {result.rotated}. Ilegíveis: {result.unreadable}.")
    print(f"Backup anterior à rotação: {backup}. Apague-o depois de conferir.")


def _delete_user(settings: Settings, username: str, *, yes: bool) -> None:
    """SEC-24 (`02-architecture.md`, "Exclusão de Usuário pelo Operador"). Um commit apaga
    as linhas; depois dele, os diretórios em `/audios`."""
    username = username.strip()
    if not auth_service.is_valid_username(username):
        raise CommandError("nome de usuário inválido: 3 a 30 letras, dígitos, _, . ou -.")
    db = settings.database_path
    if not db.exists():
        raise CommandError(f"banco {db} não existe.")
    with RunLock(db.with_name("snook.lock")):
        engine = create_db_engine(db)
        try:
            factory = create_session_factory(engine)
            with UnitOfWork(factory, lambda _event: None) as uow:
                user = auth_service.find_user_by_username(uow, username)
                if user is None:
                    raise CommandError(f"usuário {username!r} não encontrado.")
                if not yes:
                    typed = input(
                        f"Apagar {user.username!r} e todas as reuniões? Digite o nome de novo: "
                    )
                    if typed.strip() != username:
                        raise CommandError("confirmação diferente do nome: nada foi apagado.")
                meeting_ids = meetings_service.list_meeting_ids_for_user(uow, user.id)
                auth_service.delete_user(uow, user.id)
        finally:
            engine.dispose()
        meetings_service.remove_meeting_files(settings.audio_root, meeting_ids)  # SEC-15
    logger.info(
        "operator.user_deleted", extra={"user_id": user.id, "meetings_count": len(meeting_ids)}
    )
    print(f"Usuário apagado com {len(meeting_ids)} reunião(ões).")


def _download_models(settings: Settings) -> None:
    """Não escreve no banco: roda com o backend no ar, sem a trava."""
    if settings.models_offline:
        raise CommandError("MODELS_OFFLINE=true: desligue para baixar os modelos.")
    try:
        transcription_service.download_models(settings)
    except EngineFailure as failure:
        raise CommandError(failure.message) from None
    logger.info("operator.models_downloaded")
    print(f"Modelos prontos em {settings.models_root}.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m snook.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "rotate-master-key",
        help="recifra as chaves de LLM com SNOOK_MASTER_KEY; lê a anterior de "
        "SNOOK_MASTER_KEY_PREVIOUS",
    )
    delete_user = commands.add_parser(
        "delete-user",
        help="apaga o Usuário, as reuniões e os arquivos; backend parado",
    )
    delete_user.add_argument("username")
    delete_user.add_argument("--yes", action="store_true", help="pula a confirmação")
    commands.add_parser(
        "download-models",
        help="baixa Whisper e Pyannote (revisão fixa) para MODELS_ROOT; usa HF_TOKEN",
    )
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        setup_logging(settings)
        if args.command == "rotate-master-key":
            _rotate_master_key(settings)
        elif args.command == "delete-user":
            _delete_user(settings, args.username, yes=args.yes)
        elif args.command == "download-models":
            _download_models(settings)
    except (SettingsError, RunLockError, CommandError, UnsafePathError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
