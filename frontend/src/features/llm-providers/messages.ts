import type { ConfigState, Provider } from "./api"

export const PROVIDER_LABELS: Record<Provider, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
  ollama: "Ollama",
}

export const STATE_LABELS: Record<ConfigState, string> = {
  not_configured: "Não configurado",
  configured: "Configurado",
  active: "Ativo",
}

// ADR-0013.
export const OLLAMA_URL_HINT = "Sugestão: http://host.docker.internal:11434"

export const MESSAGES = {
  title: "Configurações",
  description:
    "Provedores de LLM que geram o backlog. O provedor ativo processa suas reuniões.",
  loadError: "Não foi possível carregar as configurações.",
  loading: "Carregando configurações…",
  apiKey: "Chave de API",
  url: "URL",
  model: "Modelo",
  contextWindow: "Janela de contexto",
  contextWindowHint: "Em tokens.",
  invalidContextWindow: "Informe um número inteiro positivo.",
  keepKey: (mask: string) => `Deixe vazio para manter a chave atual (${mask}).`,
  keyUnreadable: "Chave ilegível. Digite a chave de novo.",
  key: "Chave",
  notSet: "—",
  tokens: (n: number) => `${n.toLocaleString("pt-BR")} tokens`,
  test: "Testar conexão",
  testing: "Testando…",
  testOk: "Conexão bem-sucedida.",
  save: "Salvar",
  saving: "Salvando…",
  saved: "Configuração salva.",
  saveHint: "Teste a conexão com os valores atuais para liberar o Salvar.",
  activate: "Tornar ativo",
  remove: "Remover",
  removeTitle: (provider: string) => `Remover ${provider}?`,
  removeDescription:
    "A configuração e a chave cifrada são apagadas. Se este for o provedor ativo, você fica sem provedor ativo até escolher outro.",
  removeConfirm: "Remover configuração",
  cancel: "Cancelar",
}
