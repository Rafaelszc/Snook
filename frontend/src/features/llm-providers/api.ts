// 05-api.md, `llm-providers`. A API nunca devolve a chave: só `key_mask`.
export type Provider = "openai" | "anthropic" | "deepseek" | "ollama"

export type ConfigState = "not_configured" | "configured" | "active"

export interface LlmConfig {
  provider: Provider
  state: ConfigState
  model: string | null
  context_window: number | null
  key_mask: string | null
  base_url: string | null
  key_status: "ok" | "unreadable" | null
  default_model: string
  default_context_window: number
}

// Campo ausente: o servidor usa o valor salvo, senão o padrão (ADR-0013).
export interface ConfigDraft {
  api_key?: string
  base_url?: string
  model?: string
  context_window?: number
}

export type ConnectionResult =
  { ok: true } | { ok: false; reason: string; message: string }

export const llmConfigsQueryKey = ["llm-configs"] as const
