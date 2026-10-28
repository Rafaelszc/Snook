import type { Status } from "@/components/surfaces/StatusBadge"

// 05-api.md, `participants`.
export interface Speaker {
  speaker_label: string
  total_seconds: number
}

export interface Participant {
  id: number
  name: string
  speaker_labels: string[]
}

// Parte do detalhe da Reunião (`GET /meetings/{id}`) que a tela precisa.
export interface MeetingNamingState {
  status: Status
  participants_confirmed: boolean
}

// Parte de `GET /llm-configs` que a tela precisa (05-api.md, `llm-providers`).
export interface LlmConfigState {
  provider: string
  state: "not_configured" | "configured" | "active"
  model: string | null
}

export const sampleUrl = (meetingId: string, label: string) =>
  `/api/meetings/${meetingId}/speakers/${encodeURIComponent(label)}/sample`

// Nomeação só em `transcribed` sem confirmação (`participants` 25).
export function canName(meeting: MeetingNamingState): boolean {
  return meeting.status === "transcribed" && !meeting.participants_confirmed
}

// Mesma regra do backend: ignora maiúsculas e espaços nas pontas (`participants` 7).
export const nameKey = (name: string) => name.trim().toLocaleLowerCase("pt-BR")

// Rótulo -> outros rótulos com o mesmo nome (`participants` 27).
export function mergeGroups(
  names: Record<string, string>
): Map<string, string[]> {
  const byKey = new Map<string, string[]>()
  for (const [label, name] of Object.entries(names)) {
    const key = nameKey(name)
    if (!key) continue
    byKey.set(key, [...(byKey.get(key) ?? []), label])
  }
  const result = new Map<string, string[]>()
  for (const labels of byKey.values()) {
    if (labels.length < 2) continue
    for (const label of labels)
      result.set(
        label,
        labels.filter((other) => other !== label)
      )
  }
  return result
}
