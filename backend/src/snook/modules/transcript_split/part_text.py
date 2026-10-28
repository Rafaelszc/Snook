"""Texto da Parte: uma linha por segmento, `[hh:mm:ss] Nome: texto` (`transcript-split` 25)."""


def format_timestamp(seconds: float) -> str:
    """Instante absoluto na gravação, truncado ao segundo."""
    total = int(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def format_line(start_seconds: float, name: str, text: str) -> str:
    """Espaços e quebras viram um espaço: um segmento = uma linha (estimativa aditiva, ADR-0011)."""
    return f"[{format_timestamp(start_seconds)}] {' '.join(name.split())}: {' '.join(text.split())}"
