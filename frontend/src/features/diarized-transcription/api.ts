import type { Status } from "@/components/surfaces/StatusBadge"

// 05-api.md, `diarized-transcription`.
export interface TranscriptSegment {
  id: number
  speaker_label: string
  start_seconds: number
  end_seconds: number
  text: string
}

export interface Transcript {
  segments: TranscriptSegment[]
}

export const transcriptQueryKey = (meetingId: string) =>
  ["meetings", meetingId, "transcript"] as const

// Parte do detalhe da Reunião (`GET /meetings/{id}`) que a tela precisa.
export interface MeetingStatus {
  status: Status
  failed_stage: "transcription" | "generation" | null
}

export const meetingStatusQueryKey = (meetingId: string) =>
  ["meetings", meetingId, "transcript-status"] as const

const NOT_READY: ReadonlySet<Status> = new Set(["pending", "processing"])

// Antes de `transcribed`, ou `failed` na transcrição, não há texto (`diarized-transcription` 19).
export function hasTranscript(meeting: MeetingStatus): boolean {
  return (
    !NOT_READY.has(meeting.status) &&
    !(meeting.status === "failed" && meeting.failed_stage === "transcription")
  )
}

// `GET /meetings/{id}/participants` (05-api.md, `participants`).
export interface Participant {
  id: string
  name: string
  speaker_labels: string[]
}

export const participantsQueryKey = (meetingId: string) =>
  ["meetings", meetingId, "transcript-participants"] as const
