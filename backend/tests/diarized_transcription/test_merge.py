from pathlib import Path

import pytest

from snook.core.db import create_db_engine, create_session_factory
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import repository, service
from snook.modules.diarized_transcription.engines.base import Chunk, Turn
from snook.modules.diarized_transcription.merge import Segment, Speaker, merge, speakers
from tests.diarized_transcription.test_storage_fakes import MEETING_ID, db  # noqa: F401

TURNS = [Turn("SPEAKER_00", 0.0, 10.0), Turn("SPEAKER_01", 20.0, 30.0)]


@pytest.mark.parametrize(
    ("chunk", "label"),
    [
        (Chunk(2.0, 8.0, "dentro"), "SPEAKER_00"),
        (Chunk(21.0, 25.0, "dentro"), "SPEAKER_01"),
        (Chunk(8.0, 24.0, "cruza mais o 01"), "SPEAKER_01"),
        (Chunk(5.0, 21.0, "cruza mais o 00"), "SPEAKER_00"),
        (Chunk(11.0, 13.0, "entre, perto do 00"), "SPEAKER_00"),
        (Chunk(17.0, 19.0, "entre, perto do 01"), "SPEAKER_01"),
        (Chunk(32.0, 35.0, "depois de todos"), "SPEAKER_01"),
    ],
)
def test_chunk_gets_speaker_by_overlap_or_nearest_turn(chunk: Chunk, label: str) -> None:
    """`diarized-transcription` 9, 10."""
    [segment] = merge(TURNS, [chunk], duration_seconds=40.0)
    assert segment.speaker_label == label


def test_no_segment_without_speaker() -> None:
    chunks = [Chunk(float(s), float(s) + 1.0, f"t{s}") for s in range(0, 40, 3)]
    segments = merge(TURNS, chunks, duration_seconds=40.0)
    assert segments
    assert all(s.speaker_label in {"SPEAKER_00", "SPEAKER_01"} for s in segments)


def test_same_speaker_with_short_pause_joins() -> None:
    chunks = [Chunk(0.0, 2.0, "Bom dia,"), Chunk(3.0, 5.0, "vamos começar.")]
    assert merge(TURNS, chunks, duration_seconds=40.0) == [
        Segment("SPEAKER_00", 0.0, 5.0, "Bom dia, vamos começar.")
    ]


def test_pause_of_exactly_one_second_joins() -> None:
    chunks = [Chunk(0.0, 2.0, "a"), Chunk(3.0, 4.0, "b"), Chunk(5.0, 6.0, "c")]
    assert merge(TURNS, chunks, duration_seconds=40.0) == [Segment("SPEAKER_00", 0.0, 6.0, "a b c")]


def test_long_pause_or_other_speaker_keeps_apart() -> None:
    chunks = [
        Chunk(0.0, 2.0, "a"),
        Chunk(3.5, 4.0, "pausa longa"),
        Chunk(4.5, 10.0, "fim do 00"),
        Chunk(10.5, 22.0, "já é do 01"),
    ]
    segments = merge(TURNS, chunks, duration_seconds=40.0)
    assert [(s.speaker_label, s.text) for s in segments] == [
        ("SPEAKER_00", "a"),
        ("SPEAKER_00", "pausa longa fim do 00"),
        ("SPEAKER_01", "já é do 01"),
    ]


def test_segments_are_valid_and_ordered() -> None:
    """`diarized-transcription` 11, 12."""
    chunks = [
        Chunk(25.0, 28.0, "terceiro"),
        Chunk(-0.5, 2.0, "  começo antes do zero "),
        Chunk(12.0, 14.0, "   "),
        Chunk(38.0, 45.0, "passa do fim"),
        Chunk(15.0, 15.0, "sem duração"),
        Chunk(41.0, 43.0, "todo depois do fim"),
        Chunk(11.0, 12.0, "segundo"),
    ]
    segments = merge(TURNS, chunks, duration_seconds=40.0)
    assert [s.text for s in segments] == [
        "começo antes do zero",
        "segundo",
        "terceiro",
        "passa do fim",
    ]
    assert all(0 <= s.start_seconds < s.end_seconds <= 40.0 for s in segments)
    assert all(s.text == s.text.strip() and s.text for s in segments)
    starts = [s.start_seconds for s in segments]
    assert starts == sorted(starts)


def test_no_turns_gives_no_segments() -> None:
    assert merge([], [Chunk(0.0, 1.0, "x")], duration_seconds=40.0) == []


def test_speakers_are_exactly_segment_labels_with_totals() -> None:
    """`diarized-transcription` 13."""
    segments = [
        Segment("SPEAKER_01", 0.0, 2.0, "a"),
        Segment("SPEAKER_00", 3.0, 8.0, "b"),
        Segment("SPEAKER_01", 9.0, 15.0, "c"),
        Segment("SPEAKER_01", 16.0, 17.0, "d"),
    ]
    assert speakers(segments) == [
        Speaker("SPEAKER_00", total_seconds=5.0, longest=segments[1]),
        Speaker("SPEAKER_01", total_seconds=9.0, longest=segments[2]),
    ]


def test_speakers_of_empty_transcript() -> None:
    assert speakers([]) == []


def test_service_lists_speakers_from_stored_segments(db: Path) -> None:  # noqa: F811
    factory = create_session_factory(create_db_engine(db))
    stored = [Segment("SPEAKER_00", 0.0, 4.0, "a"), Segment("SPEAKER_02", 5.0, 6.0, "b")]
    with UnitOfWork(factory, lambda _: None) as uow:
        repository.add_segments(uow.session, MEETING_ID, stored)
    with UnitOfWork(factory, lambda _: None) as uow:
        assert [s.speaker_label for s in service.list_speakers(uow, MEETING_ID)] == [
            "SPEAKER_00",
            "SPEAKER_02",
        ]
