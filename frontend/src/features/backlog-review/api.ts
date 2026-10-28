import type { Status } from "@/components/surfaces/StatusBadge"

// 05-api.md, `backlog-review`. Texto vindo da LLM: só renderizado escapado (SEC-12).
export interface Requester {
  id: number
  name: string
}

export interface Criterion {
  id: number
  given: string
  when: string
  then: string
}

export type Priority = "Low" | "Medium" | "High"

export interface UserStory {
  id: number
  us_id: string
  name: string
  as_a: string
  i_want: string
  so_that: string
  priority: Priority
  story_points: number
  requested_by: Requester | null
  requested_at: string | null
  acceptance_criteria: Criterion[]
}

export interface Epic {
  id: number
  name: string
  user_stories: UserStory[]
}

export interface Backlog {
  read_only: boolean
  last_generation_failed: boolean
  epics: Epic[]
}

export interface Participant {
  id: number
  name: string
}

// Parte do `GET /api/meetings/{id}` que a revisão usa.
export interface ReviewMeeting {
  id: string
  title: string
  status: Status
  participants_confirmed: boolean
  has_backlog: boolean
  failed_stage: "transcription" | "generation" | null
  error_message: string | null
}

export type RegenerateMode = "same_cuts" | "adjust_cuts"
export type ExportFormat = "md" | "json"

export const PRIORITIES: readonly Priority[] = ["Low", "Medium", "High"]
export const STORY_POINTS: readonly number[] = [1, 2, 3, 5, 8, 13]

export const meetingKey = (id: string) => ["meetings", id] as const
export const backlogKey = (id: string) => ["meetings", id, "backlog"] as const
export const participantsKey = (id: string) =>
  ["meetings", id, "participants"] as const

export const exportUrl = (id: string, format: ExportFormat) =>
  `/api/meetings/${id}/export?format=${format}`

// Mesma regra do backend: sem diferenciar caixa e espaços nas pontas (Q47, Q55).
export function sameName(a: string, b: string): boolean {
  const norm = (value: string) => value.trim().toLocaleLowerCase("pt-BR")
  return norm(a) !== "" && norm(a) === norm(b)
}

// Nome de outro item da lista igual a `draft`: os dois serão juntados (`backlog-review` 41).
export function mergeTarget<T extends { id: number; name: string }>(
  items: readonly T[],
  selfId: number | null,
  draft: string
): T | undefined {
  return items.find((item) => item.id !== selfId && sameName(item.name, draft))
}

// Regras por status (`backlog-review`, tabela): renomear participante só fora de `generating`.
export function canRenameParticipant(meeting: ReviewMeeting): boolean {
  if (meeting.status === "failed") return meeting.failed_stage === "generation"
  return ["done", "transcribed", "needs_split"].includes(meeting.status)
}

const ACTIVE: ReadonlySet<Status> = new Set([
  "pending",
  "processing",
  "generating",
])

export function isActive(meeting: ReviewMeeting): boolean {
  return (
    ACTIVE.has(meeting.status) ||
    (meeting.status === "transcribed" && meeting.participants_confirmed)
  )
}
