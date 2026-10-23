import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import Executor, Future
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from snook.core.events import MeetingCreated, RetryRequested
from snook.core.settings import Settings
from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.dispatcher import TranscriptionDispatcher, process_pool
from snook.modules.diarized_transcription.engines.base import EngineFailure
from snook.modules.diarized_transcription.engines.fakes import CHUNKS, FakeEngines, fake_engines
from snook.modules.diarized_transcription.pipeline import Job, default_engines, run_job
from snook.modules.meetings.media_probe import ProbeResult
from tests.auth.helpers import rows
from tests.diarized_transcription.conftest import install, wait_for
from tests.diarized_transcription.helpers import create, digest, segments, state
from tests.meetings.helpers import URL, FakeProbe, set_fields

pytestmark = pytest.mark.usefixtures("probe", "clock")

EXPECTED_SEGMENTS = [
    (0, "SPEAKER_00", 0.5, 4.5, "Bom dia, vamos começar."),
    (1, "SPEAKER_01", 5.5, 9.5, "Preciso de um relatório."),
]


def _dir(settings: Settings, meeting_id: str) -> Path:
    return settings.audio_root / meeting_id


def _tmp_files(settings: Settings) -> list[Path]:
    return list((settings.audio_root / ".tmp").iterdir())


def _publish(client: TestClient, event: object) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.event_bus.publish(event)


def _run_id(settings: Settings, meeting_id: str) -> str:
    [(run_id,)] = rows(
        settings.database_path,
        f"SELECT run_id FROM meetings WHERE id = '{meeting_id}'",  # noqa: S608
    )
    return str(run_id)


def test_created_meeting_goes_processing_then_transcribed(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher, engines: FakeEngines
) -> None:
    """`diarized-transcription` 1."""
    seen: list[str] = []
    treat = engines.audio.treat

    def spy(source: Path, target: Path) -> None:
        seen.append(state(settings.database_path, source.parent.name)[0])
        treat(source, target)

    engines.audio.treat = spy  # type: ignore[method-assign]

    meeting_id = create(ana)

    assert seen == ["processing"]
    assert state(settings.database_path, meeting_id) == ("transcribed", None, None)
    assert segments(settings.database_path, meeting_id) == EXPECTED_SEGMENTS
    assert (_dir(settings, meeting_id) / "treated.flac").exists()
    assert _tmp_files(settings) == []
    assert dispatcher.running == 0


def test_retry_discards_previous_data_and_reprocesses_original(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher
) -> None:
    """`diarized-transcription` 2: inclusive sobra de tentativa interrompida por reinício."""
    dispatcher.engines = fake_engines("transcription_failure")
    meeting_id = create(ana)
    assert state(settings.database_path, meeting_id)[0] == "failed"
    db = settings.database_path
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO transcript_segments (meeting_id, position, speaker_label, "
            "start_seconds, end_seconds, text) VALUES (?, 0, 'SPEAKER_09', 0, 1, 'velho')",
            (meeting_id,),
        )
    (_dir(settings, meeting_id) / "treated.flac").write_bytes(b"velho")
    engines = fake_engines()
    dispatcher.engines = engines

    response = ana.post(f"{URL}/{meeting_id}/retry")

    assert response.status_code == 202
    assert state(db, meeting_id) == ("transcribed", None, None)
    assert segments(db, meeting_id) == EXPECTED_SEGMENTS
    assert (_dir(settings, meeting_id) / "treated.flac").read_bytes() != b"velho"
    assert engines.audio.sources == [_dir(settings, meeting_id) / "original.mp3"]


@pytest.mark.parametrize("event_type", ["created", "retry"])
@pytest.mark.parametrize("status", ["processing", "transcribed", "failed"])
def test_event_outside_pending_is_ignored(
    ana: TestClient,
    settings: Settings,
    dispatcher: TranscriptionDispatcher,
    engines: FakeEngines,
    status: str,
    event_type: str,
) -> None:
    """`diarized-transcription` 3: aviso repetido ou com a Reunião já em andamento."""
    meeting_id = create(ana)
    extra: dict[str, Any] = {}
    if status == "failed":
        extra = {"failed_stage": "transcription", "error_message": "falhou"}
    set_fields(settings.database_path, meeting_id, status=status, **extra)
    before = (
        state(settings.database_path, meeting_id),
        segments(settings.database_path, meeting_id),
    )
    run_id = _run_id(settings, meeting_id)
    event = (
        MeetingCreated(meeting_id=meeting_id, run_id=run_id)
        if event_type == "created"
        else RetryRequested(meeting_id=meeting_id, run_id=run_id, stage="transcription")
    )

    _publish(ana, event)

    assert len(engines.audio.sources) == 1
    after = (
        state(settings.database_path, meeting_id),
        segments(settings.database_path, meeting_id),
    )
    assert after == before


def test_generation_retry_is_not_consumed(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher, engines: FakeEngines
) -> None:
    meeting_id = create(ana)
    set_fields(settings.database_path, meeting_id, status="pending")
    run_id = _run_id(settings, meeting_id)

    _publish(ana, RetryRequested(meeting_id=meeting_id, run_id=run_id, stage="generation"))

    assert len(engines.audio.sources) == 1
    assert state(settings.database_path, meeting_id)[0] == "pending"


def test_original_file_does_not_change(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher
) -> None:
    """`diarized-transcription` 4."""
    meeting_id = create(ana, content=b"ID3 original intacto")

    original = _dir(settings, meeting_id) / "original.mp3"
    assert original.read_bytes() == b"ID3 original intacto"
    assert state(settings.database_path, meeting_id)[0] == "transcribed"


def test_original_digest_is_the_same_after_retry(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher
) -> None:
    meeting_id = create(ana)
    original = _dir(settings, meeting_id) / "original.mp3"
    before = digest(original)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="transcription",
        error_message="x",
    )
    ana.post(f"{URL}/{meeting_id}/retry")
    assert digest(original) == before


@pytest.mark.parametrize(("sent", "expected"), [("3", 3), (None, None)])
def test_expected_speakers_reaches_diarization(
    ana: TestClient,
    dispatcher: TranscriptionDispatcher,
    engines: FakeEngines,
    sent: str | None,
    expected: int | None,
) -> None:
    """`diarized-transcription` 7."""
    data = {} if sent is None else {"expected_speakers": sent}
    create(ana, **data)
    assert engines.diarizer.calls == [expected]


def test_language_is_always_pt(
    ana: TestClient, dispatcher: TranscriptionDispatcher, engines: FakeEngines
) -> None:
    """`diarized-transcription` 8."""
    create(ana)
    create(ana)
    assert engines.transcriber.languages == ["pt", "pt"]


@pytest.mark.parametrize(
    ("outcome", "message"),
    [
        ("audio_failure", messages.AUDIO_FAILED),
        ("diarization_failure", messages.DIARIZATION_FAILED),
        ("transcription_failure", messages.TRANSCRIPTION_FAILED),
    ],
)
def test_engine_failure_goes_failed_without_partial_segments(
    ana: TestClient,
    settings: Settings,
    dispatcher: TranscriptionDispatcher,
    outcome: str,
    message: str,
) -> None:
    """`diarized-transcription` 14."""
    dispatcher.engines = fake_engines(outcome)  # type: ignore[arg-type]

    meeting_id = create(ana)

    assert state(settings.database_path, meeting_id) == ("failed", "transcription", message)
    assert segments(settings.database_path, meeting_id) == []
    assert not (_dir(settings, meeting_id) / "treated.flac").exists()
    assert _tmp_files(settings) == []
    detail = ana.get(f"{URL}/{meeting_id}").json()
    assert (detail["failed_stage"], detail["error_message"]) == ("transcription", message)


def test_hf_token_failure_cites_token_and_terms_without_value(
    ana: TestClient,
    settings: Settings,
    dispatcher: TranscriptionDispatcher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`diarized-transcription` 15."""
    token = "hf_tokenSecretoDeTeste123"
    settings.hf_token = SecretStr(token)
    dispatcher.engines = fake_engines("hf_token")
    caplog.set_level(logging.DEBUG)

    meeting_id = create(ana)

    status, stage, message = state(settings.database_path, meeting_id)
    assert (status, stage) == ("failed", "transcription")
    assert "HF_TOKEN" in message and "termos" in message
    assert token not in message
    assert token not in caplog.text


def test_no_speech_goes_failed(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher
) -> None:
    """`diarized-transcription` 16."""
    dispatcher.engines = fake_engines("no_speech")

    meeting_id = create(ana)

    assert state(settings.database_path, meeting_id) == (
        "failed",
        "transcription",
        "nenhuma fala detectada",
    )
    assert segments(settings.database_path, meeting_id) == []


def test_deleted_during_processing_saves_nothing(
    ana: TestClient,
    settings: Settings,
    held: FakeEngines,
    threaded: Callable[..., TranscriptionDispatcher],
) -> None:
    """`diarized-transcription` 17."""
    dispatcher = threaded(workers=2, max_per_user=1)
    meeting_id = create(ana)
    assert held.audio.wait_started(meeting_id)

    assert ana.delete(f"{URL}/{meeting_id}").status_code == 204
    held.audio.release(meeting_id)
    wait_for(lambda: dispatcher.running == 0)

    assert rows(settings.database_path, "SELECT COUNT(*) FROM transcript_segments") == [(0,)]
    assert not _dir(settings, meeting_id).exists()
    assert _tmp_files(settings) == []


def test_unexpected_engine_error_goes_failed(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher, engines: FakeEngines
) -> None:
    """SEC-19: exceção fora do previsto vira `failed`, nunca status preso."""

    def boom(audio: Path, num_speakers: int | None) -> list[Any]:
        raise RuntimeError("detalhe interno /models/x")

    engines.diarizer.diarize = boom  # type: ignore[method-assign]

    meeting_id = create(ana)

    assert state(settings.database_path, meeting_id) == (
        "failed",
        "transcription",
        messages.UNEXPECTED,
    )


class _BrokenExecutor(Executor):
    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Future[Any]:
        raise RuntimeError("pool quebrado")


def test_submit_failure_goes_failed(
    ana: TestClient, settings: Settings, engines: FakeEngines
) -> None:
    """SEC-19: o trabalho nem começou e a Reunião não fica presa em `processing`."""
    dispatcher = install(ana, engines, lambda _n: _BrokenExecutor(), workers=2, max_per_user=1)

    meeting_id = create(ana)

    assert state(settings.database_path, meeting_id) == (
        "failed",
        "transcription",
        messages.UNEXPECTED,
    )
    assert dispatcher.running == 0


def test_transcript_text_never_reaches_logs(
    ana: TestClient, dispatcher: TranscriptionDispatcher, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20."""
    caplog.set_level(logging.DEBUG)
    create(ana)
    assert "transcription.done" in caplog.text
    for chunk in CHUNKS:
        assert chunk.text not in caplog.text


def test_segments_end_within_audio_duration(
    ana: TestClient, probe: FakeProbe, settings: Settings, dispatcher: TranscriptionDispatcher
) -> None:
    """`0 <= start < end <= duração`: a duração vem do upload."""
    probe.result = ProbeResult(has_audio=True, duration_seconds=7.0)
    meeting_id = create(ana)
    assert segments(settings.database_path, meeting_id)[-1][3] == 7.0


def test_job_runs_in_spawned_process(tmp_path: Path) -> None:
    """ADR-0007: trabalho e engines atravessam o `ProcessPoolExecutor` (`spawn`)."""
    job = Job(
        original_path=tmp_path / "original.mp3",
        treated_path=tmp_path / "t.flac",
        duration_seconds=60.0,
        expected_speakers=None,
    )
    pool = process_pool(1)
    try:
        future = pool.submit(run_job, default_engines(), job)
        with pytest.raises(EngineFailure) as caught:
            future.result(timeout=60)
    finally:
        pool.shutdown()
    assert caught.value.message == messages.ENGINES_UNAVAILABLE
