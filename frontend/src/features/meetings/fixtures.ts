import type { MeetingDetail, MeetingSummary } from "./api"

export const MEETING_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"

export const SUMMARY: MeetingSummary = {
  id: MEETING_ID,
  title: "Planejamento do trimestre",
  created_at: "2026-10-23T12:00:00Z",
  duration_seconds: 3725,
  status: "pending",
  participants_confirmed: false,
}

export function detail(overrides: Partial<MeetingDetail> = {}): MeetingDetail {
  return {
    ...SUMMARY,
    original_filename: "planejamento.mp3",
    expected_speakers: 3,
    has_backlog: false,
    failed_stage: null,
    error_message: null,
    split_reason: null,
    ...overrides,
  }
}

export function apiError(
  status: number,
  code: string,
  message: string,
  fields = {}
) {
  return { status, body: { error: { code, message, fields } } }
}
