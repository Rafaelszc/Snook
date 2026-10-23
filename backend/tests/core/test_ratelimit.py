from datetime import UTC, datetime, timedelta

from snook.core.clock import FakeClock
from snook.core.ratelimit import SlidingWindowLimiter

_START = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def _limiter(max_events: int = 3, window_seconds: int = 60) -> SlidingWindowLimiter:
    return SlidingWindowLimiter(max_events=max_events, window_seconds=window_seconds)


def test_denies_after_n_events_with_retry_after() -> None:
    clock = FakeClock(_START)
    limiter = _limiter()
    for _ in range(3):
        assert limiter.retry_after("k", clock.now()) == 0
        limiter.hit("k", clock.now())
        clock.advance(timedelta(seconds=10))
    # Primeiro evento em t=0, agora t=30: libera em t=60.
    assert limiter.retry_after("k", clock.now()) == 30


def test_retry_after_rounds_up_to_whole_seconds() -> None:
    limiter = _limiter(max_events=1)
    limiter.hit("k", _START)
    assert limiter.retry_after("k", _START + timedelta(seconds=59.2)) == 1


def test_window_passing_releases() -> None:
    clock = FakeClock(_START)
    limiter = _limiter()
    for _ in range(3):
        limiter.hit("k", clock.now())
    clock.advance(timedelta(seconds=60))
    assert limiter.retry_after("k", clock.now()) == 0


def test_sliding_window_releases_one_event_at_a_time() -> None:
    clock = FakeClock(_START)
    limiter = _limiter()
    limiter.hit("k", clock.now())
    clock.advance(timedelta(seconds=30))
    limiter.hit("k", clock.now())
    limiter.hit("k", clock.now())
    clock.advance(timedelta(seconds=30))
    # Saiu só o evento de t=0; os de t=30 seguem na janela.
    assert limiter.retry_after("k", clock.now()) == 0
    limiter.hit("k", clock.now())
    assert limiter.retry_after("k", clock.now()) == 30


def test_keys_are_independent() -> None:
    limiter = _limiter()
    for _ in range(3):
        limiter.hit("a", _START)
    assert limiter.retry_after("a", _START) > 0
    assert limiter.retry_after("b", _START) == 0


def test_reset_clears_key() -> None:
    limiter = _limiter()
    for _ in range(3):
        limiter.hit("a", _START)
        limiter.hit("b", _START)
    limiter.reset("a")
    assert limiter.retry_after("a", _START) == 0
    assert limiter.retry_after("b", _START) > 0


def test_expired_keys_are_dropped() -> None:
    """Memória não cresce com chaves antigas."""
    limiter = _limiter(max_events=1)
    for i in range(5000):
        limiter.hit(f"k{i}", _START)
    limiter.hit("late", _START + timedelta(seconds=61))
    assert len(limiter) < 5000
