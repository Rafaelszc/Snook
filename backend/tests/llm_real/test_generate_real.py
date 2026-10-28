import pytest

from snook.core.settings import load_settings
from snook.modules.backlog_generation.runner import build_content
from snook.modules.backlog_generation.validation import parse_backlog
from snook.modules.llm_providers.adapters.base import GenerationRequest, ProviderTarget
from snook.modules.llm_providers.service import build_adapters
from snook.modules.transcript_split.budget import output_reserve
from snook.shared.prompts import load_backlog_response_schema, load_backlog_system_prompt
from tests.conftest import VALID_MASTER_KEY

pytestmark = pytest.mark.llm_real

DURATION_SECONDS = 120.0
PART_TEXT = "\n".join(
    [
        "[00:00:05] Ana: Bom dia. Hoje vamos falar do cadastro de clientes.",
        "[00:00:20] Ana: Preciso que o atendente cadastre cliente pessoa física com CPF.",
        "[00:00:41] Bruno: Certo. E o CPF tem que ser validado antes de salvar?",
        "[00:00:55] Ana: Sim, CPF inválido não pode ser salvo.",
        "[00:01:20] Bruno: Também quero buscar cliente pelo nome na lista.",
        "[00:01:45] Ana: Combinado.",
    ]
)


PARTICIPANTS = ["Ana", "Bruno"]


def test_generate_real(target: tuple[str, ProviderTarget], monkeypatch: pytest.MonkeyPatch) -> None:
    """Transversal 3, RT-01: resposta real passa na validação e sai no formato do backlog."""
    provider, provider_target = target
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    adapter = build_adapters(load_settings())[provider]
    assert provider_target.context_window is not None
    participants_text = "Participantes:\n" + "\n".join(f"- {name}" for name in PARTICIPANTS)
    request = GenerationRequest(
        system_prompt=load_backlog_system_prompt(),
        content=build_content(participants_text, PART_TEXT, []),
        json_schema=load_backlog_response_schema(),
        max_output_tokens=output_reserve(provider_target.context_window),
    )

    backlog = parse_backlog(
        adapter.generate(provider_target, request), duration_seconds=DURATION_SECONDS
    )

    stories = [story for epic in backlog.epics for story in epic.user_stories]
    assert stories
    assert all(story.acceptance_criteria for story in stories)
