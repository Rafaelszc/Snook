export type Status =
  | "pending"
  | "processing"
  | "transcribed"
  | "needs_split"
  | "generating"
  | "done"
  | "failed"

export const STATUS_LABELS: Record<Status, string> = {
  pending: "Pendente",
  processing: "Processando",
  transcribed: "Transcrita",
  needs_split: "Precisa dividir",
  generating: "Gerando backlog",
  done: "Concluída",
  failed: "Falhou",
}

export const CONFIRM_CANCEL = "Cancelar"

export const THEME_LABELS = {
  group: "Tema",
  light: "Claro",
  dark: "Escuro",
  system: "Sistema",
} as const
