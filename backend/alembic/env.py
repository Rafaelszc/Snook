from pathlib import Path

from alembic import context

from snook.core.db import Base, create_db_engine
from snook.core.settings import load_settings

# Cada tarefa que cria tabela importa aqui o `models` do módulo dono, para o autogenerate ver.
from snook.modules.auth import models as _auth_models  # noqa: F401
from snook.modules.diarized_transcription import models as _transcription_models  # noqa: F401
from snook.modules.llm_providers import models as _llm_providers_models  # noqa: F401
from snook.modules.meetings import models as _meetings_models  # noqa: F401
from snook.modules.participants import models as _participants_models  # noqa: F401
from snook.modules.transcript_split import models as _transcript_split_models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def _database_path() -> Path:
    path = config.attributes.get("database_path")
    return path if path is not None else load_settings().database_path


def run_migrations() -> None:
    engine = create_db_engine(_database_path())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations()
