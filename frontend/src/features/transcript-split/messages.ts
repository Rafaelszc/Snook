import { formatTimestamp, formatTokens } from "./format"

export const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
  ollama: "Ollama",
}

export const MESSAGES = {
  title: "Dividir reunião",
  back: "Voltar à reunião",
  loading: "Carregando…",
  notFound: "Reunião não encontrada.",
  notAvailable: "Esta reunião não está esperando divisão.",
  why: (total: number, budget: number) =>
    `A transcrição tem cerca de ${formatTokens(total)} tokens, e cada parte enviada ao modelo cabe em até ${formatTokens(budget)}. Divida a reunião em partes: o backlog de todas sai unificado.`,
  adjust: "Reajuste os cortes antes de regenerar o backlog.",
  providerUsed: (provider: string, model: string) =>
    `Provedor ativo: ${provider}, modelo ${model}.`,
  changeModel: "Trocar de modelo nas configurações",
  openSettings: "Abrir configurações",
  segmentsLabel: "Segmentos da reunião",
  cutsHint:
    "Corte só no fim de uma fala. Num corte, as setas para cima e para baixo movem o corte para a fala vizinha.",
  cutAfter: (time: string) => `depois da fala de ${time}`,
  cutEnd: (part: number) => `Fim da parte ${part}`,
  cutHere: "Cortar aqui",
  partsLabel: "Partes",
  partName: (part: number) => `Parte ${part}`,
  partRange: (start: number, end: number) =>
    `${formatTimestamp(start)} a ${formatTimestamp(end)}`,
  partTokens: (tokens: number) => `${formatTokens(tokens)} tokens`,
  fits: "Cabe",
  tooLarge: "Não cabe",
  summary: (parts: number, over: number) =>
    over === 0
      ? `${parts} ${parts === 1 ? "parte" : "partes"}, todas cabem no modelo.`
      : `${parts} ${parts === 1 ? "parte" : "partes"}, ${over} não ${over === 1 ? "cabe" : "cabem"}. Ajuste os cortes para confirmar.`,
  confirm: "Confirmar divisão",
  confirming: "Confirmando…",
  cancel: "Cancelar divisão",
  canceling: "Cancelando…",
  cancelHint: "Mantém o backlog atual, sem regenerar.",
}
