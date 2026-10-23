"""Limitador de janela deslizante em memória (ADR-0010; SEC-06). Um processo só (ADR-0007)."""

import math
import threading
from collections import deque
from datetime import datetime, timedelta

# Acima disso, `hit` varre as chaves vencidas: memória não cresce com chave antiga.
_SWEEP_THRESHOLD = 1024


class SlidingWindowLimiter:
    """No máximo `max_events` por chave em `window_seconds`. O instante vem de quem chama."""

    def __init__(self, *, max_events: int, window_seconds: int) -> None:
        self._max = max_events
        self._window = timedelta(seconds=window_seconds)
        self._events: dict[str, deque[datetime]] = {}
        # Rotas síncronas rodam em threads do pool.
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._events)

    def retry_after(self, key: str, now: datetime) -> int:
        """Segundos até a próxima permissão; 0 se permitido."""
        with self._lock:
            events = self._prune(key, now)
            if len(events) < self._max:
                return 0
            remaining = (events[0] + self._window - now).total_seconds()
            return max(1, math.ceil(remaining))

    def hit(self, key: str, now: datetime) -> None:
        with self._lock:
            if len(self._events) > _SWEEP_THRESHOLD:
                for stale in list(self._events):
                    self._prune(stale, now)
            events = self._events.setdefault(key, deque(maxlen=self._max))
            events.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def _prune(self, key: str, now: datetime) -> deque[datetime]:
        events = self._events.get(key)
        if events is None:
            return deque()
        while events and events[0] + self._window <= now:
            events.popleft()
        if not events:
            del self._events[key]
        return events
