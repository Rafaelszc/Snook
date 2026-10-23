import type { LlmConfig } from "./api"

// Respostas de `GET /llm-configs` (05-api.md) para os testes.
export const NOT_CONFIGURED: LlmConfig[] = [
  {
    provider: "openai",
    state: "not_configured",
    model: null,
    context_window: null,
    key_mask: null,
    base_url: null,
    key_status: null,
    default_model: "gpt-5-mini",
    default_context_window: 400000,
  },
  {
    provider: "anthropic",
    state: "not_configured",
    model: null,
    context_window: null,
    key_mask: null,
    base_url: null,
    key_status: null,
    default_model: "claude-sonnet-4-5",
    default_context_window: 200000,
  },
  {
    provider: "deepseek",
    state: "not_configured",
    model: null,
    context_window: null,
    key_mask: null,
    base_url: null,
    key_status: null,
    default_model: "deepseek-chat",
    default_context_window: 128000,
  },
  {
    provider: "ollama",
    state: "not_configured",
    model: null,
    context_window: null,
    key_mask: null,
    base_url: null,
    key_status: null,
    default_model: "llama3.1:8b",
    default_context_window: 8192,
  },
]

export const CONFIGURED: LlmConfig[] = [
  {
    ...NOT_CONFIGURED[0],
    state: "active",
    model: "gpt-5",
    context_window: 300000,
    key_mask: "sk-...abcd",
    key_status: "ok",
  },
  {
    ...NOT_CONFIGURED[1],
    state: "configured",
    model: "claude-sonnet-4-5",
    context_window: 200000,
    key_mask: "...",
    key_status: "ok",
  },
  NOT_CONFIGURED[2],
  {
    ...NOT_CONFIGURED[3],
    state: "configured",
    model: "llama3.1:8b",
    context_window: 8192,
    base_url: "http://host.docker.internal:11434",
    key_status: "ok",
  },
]
