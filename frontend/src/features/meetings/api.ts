import type { Status } from "@/components/surfaces/StatusBadge"

// 05-api.md, `meetings`. Nenhuma resposta traz caminho interno (`meetings` 21).
export interface MeetingSummary {
  id: string
  title: string
  created_at: string
  duration_seconds: number
  status: Status
}

export interface MeetingDetail extends MeetingSummary {
  original_filename: string
  expected_speakers: number | null
  participants_confirmed: boolean
  has_backlog: boolean
  failed_stage: "transcription" | "generation" | null
  error_message: string | null
  split_reason: string | null
}

export const meetingsQueryKey = ["meetings"] as const
export const meetingQueryKey = (id: string) => ["meetings", id] as const

// Status com trabalho em andamento: a tela consulta a cada POLL_INTERVAL_MS (`meetings` 40).
const ACTIVE: ReadonlySet<Status> = new Set([
  "pending",
  "processing",
  "generating",
])

export function isActive(meeting: {
  status: Status
  participants_confirmed?: boolean
}): boolean {
  return (
    ACTIVE.has(meeting.status) ||
    (meeting.status === "transcribed" &&
      meeting.participants_confirmed === true)
  )
}
