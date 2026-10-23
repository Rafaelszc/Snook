import json
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "llm"


def recorded(provider: str, case: str) -> httpx.Response:
    """Resposta gravada em `tests/fixtures/llm/<provider>/<case>.json` (status, headers, corpo)."""
    data = json.loads((FIXTURES / provider / f"{case}.json").read_text())
    body = data["body"]
    content = b"" if body is None else json.dumps(body).encode()
    return httpx.Response(data["status"], headers=data["headers"], content=content)
